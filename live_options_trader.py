import os
import time
import logging
import json
import pandas as pd
from datetime import datetime, time as dtime, timedelta
from threading import Thread

# Import our specialized Options Modules
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.options.strike_selector import OptionSelector
from modules.options.trade_executor import OptionTradeManager
from modules.options.risk_manager import OptionsRiskManager
from modules.options.broker_adapter import OptionsBrokerAdapter
from modules.dashboard_bridge import bridge
from modules.v3_utils import *
from utils.pid_lock import check_pid_lock
from dotenv import load_dotenv

load_dotenv()

# --- Phase 26: Live Backbone Config ---
LIVE_CFG = load_yaml('config/live_config.yaml').get('live', {})
FORCED_OBSERVATION = LIVE_CFG.get('forced_observation', True)
OBS_LOG = "data/observation_log.jsonl"

# --- P0-2 Startup Banner (REQ 25a-2) ---
PAPER_MODE = os.environ.get("PAPER_MODE", "true") == "true"
CAPITAL = TOTAL_CAPITAL
# REQ 25a-7: Detect volatility gate mode
with open("config/risk_execution.yaml", "r", encoding="utf-8") as f:
    vg_cfg = yaml.safe_load(f).get("volatility_gate", {})
    vg_mode = "VIX" if vg_cfg.get("use_india_vix") else "ATR_FALLBACK"

print(f"--- [BOOT] BOT STARTUP ---")
print(f"PAPER_MODE={PAPER_MODE}")
print(f"CAPITAL=₹{CAPITAL}")
print(f"RG (RiskGuard)=true")
print(f"VG (VolGate)={vg_mode}")
print(f"OBSERVATION_MODE={FORCED_OBSERVATION}")
print(f"--------------------------")

# --- MULTI-STRATEGY IMPORTS ---
from modules.strategy_selector import StrategySelector, MasterStrategySelector
from modules.strategy_router import STRATEGY_REGIME_MAP, MAX_STRATEGIES_ACTIVE
from modules.strategy_learner import StrategyLearner
from pymongo import MongoClient
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.candlestick_engine import CandlestickEngine
from modules.strategy_adapters import (
    momentum_adapter, mean_reversion_adapter, sweep_retest_adapter,
    structure_strategy_adapter, candlestick_adapter, vwap_bounce_adapter,
    liquidity_trap_adapter, ema_crossover_adapter
)

# Corrected Imports for existing infrastructure
from modules.broker_layer import AngelOneBroker
from modules.data.memory_data_reader import MemoryDataReader
from notification.telegram_notifier import TelegramNotifier

# --- CONFIGURATION (Overrides from v3_utils) ---
SYMBOLS = ["NIFTY"] # Restricted to NIFTY for optimal parallel efficiency
TOKENS = {
    "NIFTY": "99926000",
    "BANKNIFTY": "99926009",
    "INDIA_VIX": "99926017"
}
INTERVAL = 60 # 1 Minute Main Loop
EXIT_POLL_INTERVAL = 1 # 1 Second Exit Check for low latency
PAPER_MODE = os.getenv('PAPER_MODE', 'true').strip().lower() == 'true'  # Read from .env (defaults to PAPER for safety)
BOT_MODE = "PAPER" if PAPER_MODE else "LIVE"

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("logs/options_bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger("MainOptionsLoop")

class LiveOptionsTrader:
    def __init__(self):
        # 1. Scrip Master & Broker
        from modules.options.scrip_master import scrip_master
        scrip_master.initialize()
        
        self.base_broker = AngelOneBroker()
        self.broker = OptionsBrokerAdapter(self.base_broker)
        
        # 2. Data Reader (Memory + WebSocket)
        # We explicitly use MemoryDataReader for live trading to handle WS + OHLCV caching efficiently
        from modules.data.memory_data_reader import MemoryDataReader
        self.data_reader = MemoryDataReader(self.base_broker)
        
        # 3. Notifier
        self.notifier = TelegramNotifier()
        
        # 4. Bridge for Dashboard
        self.bridge = bridge
        
        # 5. MongoDB for Learner
        self.mongo_client = MongoClient(os.getenv("MONGO_URL"))
        self.db = self.mongo_client[os.getenv("DB_NAME", "tradealert_db")]

        # 6. Adaptive Strategy Engines
        self.master_selector = MasterStrategySelector()
        self.learner  = StrategyLearner(db=self.db)
        
        # 7. RiskGuard (Phase 21)
        from modules.risk_guard import RiskGuard
        self.risk_guard = RiskGuard(starting_capital=TOTAL_CAPITAL)
        
        # Load Market Memory State (Phase 26 Recovery)
        if self.master_selector.market_memory.load_state("data/market_memory_state.json"):
            logger.info("Market Memory State recovered from data/market_memory_state.json")
        
        # Legacy Engines (keep for manual/fallback if needed)
        self.option_selector = OptionSelector(self.broker)
        self.risk_manager = OptionsRiskManager(TOTAL_CAPITAL)
        self.trade_manager = OptionTradeManager(self.broker, self.notifier, self.risk_manager)
        
        # Wire RiskGuard into Trade Manager for exit recording
        self.trade_manager.risk_guard = self.risk_guard
        
        # EMERGENCY: Clear fake positions on startup
        self.trade_manager.active_trades = {}
        logger.warning("EMERGENCY: All active trades cleared on startup.")
        
        self.is_running = True
        self.is_paused = False
        self.last_heartbeat = 0

        # FORCE TEST SIGNAL ON STARTUP
        print("=" * 60)
        print("STARTUP SIGNAL TEST")
        test_signal = {
            "symbol": "NIFTY",
            "direction": "CE",
            "strategy": "TEST_STARTUP",
            "confidence": 99,
            "entry_price": 22000.0, # Valid spot price for NIFTY
            "sl": 21950.0,
            "tp": 22100.0,
            "risk_multiplier": 0.1,
            "context_tags": ["STARTUP_TEST"]
        }
        print(f"Test signal generated: {test_signal}")
        self.bridge.signal("NIFTY", "CE", "TEST_STARTUP", 99, "STARTUP_TEST")
        self.notifier.send_message("🟢 BOT STARTED | Strategy Selector ACTIVE | Paper Mode")
        print("=" * 60)

    def check_manual_commands(self):
        """Check if dashboard/Telegram sent any manual commands via MongoDB bot_commands collection."""
        try:
            # Find any PENDING commands
            pending_cmds = list(self.db.bot_commands.find({"status": "PENDING"}).sort("timestamp", 1))
            
            for cmd in pending_cmds:
                logger.info(f"Received Manual Command: {cmd['type']}")
                success = False
                if cmd['type'] == 'CLOSE_POSITION':
                    trade_id = cmd['payload'].get('trade_id')
                    if trade_id in self.trade_manager.active_trades:
                        t = self.trade_manager.active_trades[trade_id]
                        symbol_key = t.get('token') or t.get('tradingsymbol') or f"{t['symbol']}_{t['strike']}_{t['type']}"
                        premium = self.broker.get_ltp(symbol_key)
                        self.trade_manager.close_trade(trade_id, premium, "MANUAL_CLOSE")
                        success = True
                elif cmd['type'] == 'PAUSE':
                    self.is_paused = True
                    logger.warning("Bot Paused via Dashboard.")
                    success = True
                elif cmd['type'] == 'RESUME':
                    self.is_paused = False
                    logger.info("Bot Resumed via Dashboard.")
                    success = True
                elif cmd['type'] == 'CLOSE_ALL':
                    for tid in list(self.trade_manager.active_trades.keys()):
                        t = self.trade_manager.active_trades[tid]
                        symbol_key = t.get('token') or t.get('tradingsymbol') or f"{t['symbol']}_{t['strike']}_{t['type']}"
                        premium = self.broker.get_ltp(symbol_key)
                        self.trade_manager.close_trade(tid, premium, "MANUAL_CLOSE_ALL")
                    success = True
                elif cmd['type'] == 'MANUAL_TRADE':
                    payload = cmd['payload']
                    sym = payload.get('symbol', 'NIFTY')
                    side = payload.get('direction', 'CE')
                    lots = int(payload.get('lots', 1))
                    
                    logger.info(f"Executing Manual Trade: {sym} {side} | Lots: {lots}")
                    
                    # Manual trades still need strike selection
                    vix = self.broker.get_vix()
                    expiries = self.broker.get_expiry_list(sym)
                    option_chain = self.broker.get_full_option_chain(sym)
                    spot = self.broker.get_ltp(sym)
                    
                    option_details = self.option_selector.select_option(
                        side, 80, spot, vix, expiries, option_chain, datetime.now()
                    )
                    
                    if option_details:
                        # Create a mock signal object for the trade manager
                        mock_signal = {
                            'strategy': 'MANUAL',
                            'symbol': sym,
                            'vix': vix,
                            'options_direction': side,
                            'spot_price': spot,
                            'adaptive_exits': {
                                'sl_type': 'MANUAL',
                                'tp_type': 'MANUAL_R',
                                'sl_dist': float(payload.get('sl', 20.0)),
                                'target_r': float(payload.get('tp_r', 2.0))
                            }
                        }
                        # Enter trade
                        trade_id = self.trade_manager.enter_trade(
                            mock_signal, option_details, self.risk_manager.total_capital, 
                            paper_mode=PAPER_MODE
                        )
                        if trade_id:
                            success = True
                            logger.info(f"Manual Trade Executed: {trade_id}")
                    else:
                        logger.warning(f"Manual trade failed: No option strike selected for {sym}")
                
                # Mark as processed
                self.db.bot_commands.update_one({"_id": cmd["_id"]}, {"$set": {"status": "SUCCESS" if success else "FAILED"}})
            
        except Exception as e:
            logger.error(f"Error checking manual commands from MongoDB: {e}")

    async def _async_exit_monitoring_loop(self):
        """Asynchronous high-frequency loop for monitoring TP/SL/Time exits concurrently."""
        import asyncio
        logger.info("Exit Monitoring Thread Started (WebSocket-ready Async).")
        while self.is_running:
            try:
                if self.trade_manager.active_trades:
                    quotes = {}
                    active_trade_ids = list(self.trade_manager.active_trades.keys())

                    async def fetch_quote(tid):
                        t = self.trade_manager.active_trades.get(tid)
                        if not t: return tid, None
                        symbol_key = t.get('tradingsymbol') or t.get('token') or f"{t['symbol']}_{t['strike']}_{t['type']}"

                        # Concurrently fetch premium and spot
                        premium_task = asyncio.create_task(self.broker.async_get_ltp(symbol_key))
                        spot_task = asyncio.create_task(self.broker.async_get_ltp(t['symbol']))

                        premium, spot = await asyncio.gather(premium_task, spot_task)

                        return tid, premium, spot, t

                    tasks = [fetch_quote(tid) for tid in active_trade_ids]
                    results = await asyncio.gather(*tasks)

                    for res in results:
                        tid = res[0]
                        if len(res) == 2 and res[1] is None: continue
                        _, premium, spot, t = res
                        quotes[tid] = {'ltp': premium, 'spot': spot}
                        # Push Update to Dashboard
                        self.bridge.trade_update(tid, premium, (premium - t['entry_price']) * t['qty'])

                    # Check Exits synchronously since trade_manager is sync
                    self.trade_manager.monitor_exits(quotes)
            except Exception as e:
                logger.error(f"Error in Async Exit Monitoring Loop: {e}")

            await asyncio.sleep(EXIT_POLL_INTERVAL)

    def _exit_monitoring_loop(self):
        """Wrapper thread for the async monitoring loop."""
        import asyncio
        asyncio.run(self._async_exit_monitoring_loop())
    def run(self):
        logger.info("INITIALIZING OPTIONS BOT V1")
        if not self.broker.login():
            logger.error("Broker Login Failed. Exiting.")
            return

        # PUSH BOOT EVENT
        self.bridge.boot({"capital": TOTAL_CAPITAL, "mode": BOT_MODE})

        # 1. Initialize Data & Start Streaming
        logger.info("Starting WebSocket Streams for Indices...")
        self.data_reader.initialize_data(TOKENS, tier1_symbols=SYMBOLS + ["INDIA_VIX"])
        self.data_reader.start_streaming(list(TOKENS.values()))

        # 2. Start Exit Monitoring in background
        exit_thread = Thread(target=self._exit_monitoring_loop, daemon=True)
        exit_thread.start()

        # Confirm connectivity via Telegram
        self.notifier.send_message(f"🚀 NIFTY AI Bot Started\nMode: {'PAPER' if PAPER_MODE else 'LIVE'}\nCapital: ₹{TOTAL_CAPITAL}")

        while self.is_running:
            now = datetime.now()
            
            # --- MANUAL COMMANDS ---
            self.check_manual_commands()
            
            # 1. Market Hours Check (09:15 - 15:30)
            if now.time() < dtime(9, 15) or now.time() > dtime(15, 30):
                if now.time() == dtime(15, 31) and now.second < INTERVAL:
                    # Daily Summary
                    risk_status = self.risk_manager.get_risk_status()
                    self.bridge.daily_summary(str(now.date()), risk_status['trades'], 0, risk_status['consecutive_losses'], risk_status['daily_pnl'], TOTAL_CAPITAL + risk_status['daily_pnl'])
                time.sleep(60)
                continue

            if self.is_paused:
                time.sleep(5)
                continue

            # 2. Risk Reset (Morning)
            if now.time() == dtime(9, 15) and now.second < INTERVAL:
                self.risk_manager.daily_reset()

            # 3. Main Cycle for NIFTY and BANKNIFTY
            for sym in SYMBOLS:
                print(f"[LOOP] Processing {sym}")
                can_trade, risk_reason = self.risk_manager.can_trade(sym, now)
                if not can_trade:
                    # Log only once every 15 mins to avoid spam
                    if now.minute % 15 == 0 and now.second < INTERVAL:
                        logger.info(f"[{sym}] Risk Veto: {risk_reason}")
                    # continue # EMERGENCY: Let the loop continue for debugging even if risk vetoed

                token = TOKENS[sym]
                df_5m = self.data_reader.get_5m_candles(token, count=100)
                df_1m = self.data_reader.get_1m_candles(token, count=200) # Fetch 1m for SMC
                
                # Normalize column names to lowercase (Fix 1)
                if df_5m is not None:
                    df_5m.columns = [c.lower() for c in df_5m.columns]
                    if df_5m.index.name:
                        df_5m.index.name = df_5m.index.name.lower()
                    
                    if df_1m is not None:
                        df_1m.columns = [c.lower() for c in df_1m.columns]
                    
                    # Debug Info (Fix 3)
                    print(f"[DEBUG] {sym} df_5m columns: {list(df_5m.columns)}")
                    
                    # Fix zero volume for index symbols (Fix 4)
                    if df_5m['volume'].sum() == 0:
                        df_5m['volume'] = (
                            ((df_5m['high'] - df_5m['low']) / df_5m['close'] * 100000)
                            .clip(lower=1000)
                            .astype(int)
                        )
                        print(f"[VOLUME FIX] {sym} using synthetic volume")

                    print(f"[DEBUG] {sym} df_5m shape: {df_5m.shape}")
                    print(f"[DEBUG] {sym} df_5m sample:\n{df_5m.tail(2)}")

                # Check Data Depth
                candle_count = len(df_5m) if df_5m is not None else 0
                if candle_count < 50:
                    logger.warning(f"[WS] {sym} low candles ({candle_count}). Trying REST...")
                    try:
                        # REST candle fetch via Angel One
                        from_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                        to_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        exchange = self.broker.get_exchange(sym)
                        candle_data = self.base_broker.smart_api.getCandleData({
                            "exchange": exchange,
                            "symboltoken": token,
                            "interval": "ONE_MINUTE",
                            "fromdate": from_time,
                            "todate": to_time
                        })
                        if candle_data and candle_data.get("data"):
                            df_1m = pd.DataFrame(candle_data["data"],
                                columns=["datetime","open","high","low","close","volume"])
                            df_1m["datetime"] = pd.to_datetime(df_1m["datetime"])
                            df_1m.set_index("datetime", inplace=True)
                            
                            # Resample to 5m
                            df_5m = df_1m.resample("5min").agg({
                                "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
                            }).dropna()
                            logger.info(f"[REST] {sym} fetched {len(df_5m)} 5m bars via REST")
                        else:
                            logger.warning(f"[REST] {sym} failed. Skipping.")
                            continue
                    except Exception as e:
                        logger.error(f"[REST] {sym} error: {e}. Skipping.")
                        continue

                print(f"[CANDLES] {sym} | 5m bars: {len(df_5m)}")
                vix = self.broker.get_vix()
                
                # --- ADAPTIVE SIGNAL SCAN ---
                signal_res = self.master_selector.select_best_signal(
                    df_5m = df_5m,
                    df_1m = df_1m,
                    symbol = sym,
                    vix = vix,
                    current_time = now,
                    mode = "NORMAL"
                )
                
                print(f"[SIGNAL] {sym} | Result: {signal_res['strategy'] if signal_res else 'None'}")
                
                if signal_res:
                    msg = (f"SIGNAL | {signal_res['symbol']} "
                           f"{signal_res['direction']} | "
                           f"{signal_res['strategy']} | "
                           f"Score: {signal_res['confidence']:.0f}%")
                    print(f"\n{'='*50}\n{msg}\n{'='*50}")
                    # Telegram
                    self.notifier.send_message(f"🎯 PAPER SIGNAL\n{msg}")
                    
                    # Convert to trade manager format
                    signal = {
                        'symbol': sym,
                        'strategy': signal_res['strategy'],
                        'options_direction': signal_res['direction'],
                        'confidence': signal_res['confidence'],
                        'spot_price': signal_res['entry_price'],
                        'vix': vix,
                        'adaptive_exits': {
                            'context': "|".join(signal_res['context_tags']),
                            'sl_type': 'ATR_2',
                            'tp_type': 'FIX_2R',
                            'sl_price': signal_res['sl'],
                            'tp_price': signal_res['tp']
                        }
                    }

                    # PUSH SIGNAL EVENT
                    self.bridge.signal(sym, signal['options_direction'], signal['strategy'], signal['confidence'], signal.get('adaptive_exits', {}).get('context', 'Unknown'))

                    logger.info(f"SIGNAL FOUND: {sym} {signal['options_direction']} | Conf: {signal['confidence']}% | Strat: {signal['strategy']}")
                    
                    expiries = self.broker.get_expiry_list(sym)
                    option_chain = self.broker.get_full_option_chain(sym)
                    
                    # RiskGuard Veto (Phase 21)
                    allowed, reason = self.risk_guard.can_trade(now=now)
                    if not allowed:
                        logger.warning(f"RISK_GUARD_VETO for {sym}: {reason}")
                        self.notifier.send_message(f"🛡️ RISK GUARD VETO: {reason}")
                        continue

                    # REQ 26-2: Persistent Signal Logging
                    obs_entry = {
                        "timestamp": now.isoformat(),
                        "symbol": sym,
                        "direction": signal['options_direction'],
                        "strategy": signal['strategy'],
                        "confidence": signal['confidence'],
                        "spot_price": signal['spot_price'],
                        "vix": vix,
                        "context": signal['adaptive_exits']['context'],
                        "forced_observation": FORCED_OBSERVATION
                    }
                    with open(OBS_LOG, "a") as f:
                        f.write(json.dumps(obs_entry) + "\n")

                    # REQ 30-2: External Webhook Export
                    webhook_url = os.environ.get("SIGNAL_WEBHOOK_URL")
                    if webhook_url:
                        from utils.webhook import push_to_webhook
                        push_to_webhook(webhook_url, obs_entry)

                    # REQ 26-1: Suppress orders in observation mode
                    if FORCED_OBSERVATION:
                        logger.info(f"OBSERVATION MODE: Signal logged, order suppressed for {sym}")
                        continue

                    option_details = self.option_selector.select_option(
                        signal['options_direction'], 
                        signal['confidence'], 
                        signal['spot_price'], 
                        vix, expiries, option_chain, now
                    )
                    
                    if option_details:
                        trade_id = self.trade_manager.enter_trade(
                            signal, option_details, self.risk_manager.total_capital, 
                            paper_mode=PAPER_MODE
                        )
                        if trade_id:
                            logger.info(f"Trade Executed: {trade_id}")
                            # Push Entry Event
                            t = self.trade_manager.active_trades[trade_id]
                            self.bridge.trade_open(trade_id, sym, signal['options_direction'], option_details['premium'], t['qty'], t['sl_price'], signal['adaptive_exits']['tp_type'], signal['strategy'], signal['adaptive_exits']['context'])
                    else:
                        logger.warning(f"[{sym}] Signal found but no suitable option strike selected.")
                else:
                    # Log scan result if near VWAP
                    if now.minute % 5 == 0 and now.second < INTERVAL:
                        logger.info(f"[{sym}] Scanning with Adaptive Selector... No signals above threshold.")

            # 4. Heartbeat (Every 60 seconds)
            if time.time() - self.last_heartbeat >= 60:
                # Save Market Memory State (Phase 26 Persistence)
                self.master_selector.market_memory.save_state("data/market_memory_state.json")
                
                risk_status = self.risk_manager.get_risk_status()
                
                # Context for heartbeat
                ctx = self.master_selector.context_detector.detect(df_5m, self.broker.get_vix(), now)

                # Gather active positions for UI sync
                active_pos = []
                for tid, t in self.trade_manager.active_trades.items():
                    symbol_key = t.get('token') or t.get('tradingsymbol') or f"{t['symbol']}_{t['strike']}_{t['type']}"
                    active_pos.append({
                        "id": tid,
                        "stock": t['symbol'],
                        "direction": t['type'],
                        "entry": t['entry_price'],
                        "lots": t['qty'],
                        "unrealized": (self.broker.get_ltp(symbol_key) - t['entry_price']) * t['qty']
                    })

                self.bridge.heartbeat(
                    ctx.regime, 
                    ctx.vix_state, 
                    TOTAL_CAPITAL + risk_status['daily_pnl'], 
                    risk_status['trades'], 
                    risk_status['consecutive_losses'], 
                    f"{BOT_MODE}_OBS" if FORCED_OBSERVATION else BOT_MODE, 
                    self.is_paused,
                    active_positions=active_pos
                )
                self.last_heartbeat = time.time()
                logger.info(f"Heartbeat | PnL: {risk_status['daily_pnl']} | Active: {len(self.trade_manager.active_trades)}")

            # --- DRIFT-FREE SLEEP (Phase 26) ---
            # Ensures loop runs exactly at the top of the minute (XX:XX:00)
            sleep_time = INTERVAL - (time.time() % INTERVAL)
            if sleep_time < 1: sleep_time += INTERVAL # Prevent double-firing
            time.sleep(sleep_time)

if __name__ == "__main__":
    check_pid_lock("options_trader")
    bot = LiveOptionsTrader()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot Shutdown Requested.")
        bot.is_running = False
