import os
import time
import json
import yaml
import pandas as pd
import logging
import csv
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from modules.price_action_engine import PriceActionEngine
from modules.broker_layer import AngelOneBroker
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.regime_gate import RegimeGate
from modules.portfolio_manager import PortfolioManager
from notification.telegram_notifier import TelegramNotifier
from modules.trailing_sl_manager import TrailingSLManager, ManagedTrade
from modules.data.memory_data_reader import MemoryDataReader
from modules.reporting.daily_report import DailyReportGenerator
from modules.reporting.equity_tracker import EquityTracker

# === VIX & EVENT FILTER START ===
# REVERT: Comment out these imports to disable advanced filters
from modules.vix_filter import VIXDirectionalFilter
from modules.event_calendar import EventCalendar
# === VIX & EVENT FILTER END ===

# 1. LOGGING CONFIGURATION
logging.basicConfig(
    filename='logs/live_trader_v3.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('live_trader')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
logger.addHandler(console_handler)

# 2. ROLLBACK CONFIGURATION
ROLLBACK_MONITORING = False
ROLLBACK_DEADLINE = None

def check_auto_rollback():
    global ROLLBACK_MONITORING, ROLLBACK_DEADLINE
    history_file = "data/optimization/param_history.json"
    if not os.path.exists(history_file): return
    try:
        with open(history_file, "r") as f: history = json.load(f)
        last_run = history[-1] if history else None
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if not last_run or last_run['date'] != yesterday: return 
        if not last_run.get('accepted'): return 
        
        ROLLBACK_MONITORING = True
        ROLLBACK_DEADLINE = datetime.now() + timedelta(hours=2)
        logger.info(f"ROLLBACK MONITORING ACTIVE until {ROLLBACK_DEADLINE.strftime('%H:%M:%S')}")
    except Exception as e: logger.error(f"Rollback Check Error: {e}")

def perform_rollback(notifier):
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        logger.warning("AUTO-ROLLBACK TRIGGERED! -3% DD detected.")
        for cfg in ["strategy_filter.yaml", "momentum.yaml", "mean_reversion.yaml", "sweep_retest.yaml"]:
            backup = f"config/backups/{cfg.split('.')[0]}_{yesterday}.yaml"
            if os.path.exists(backup):
                shutil.copy(backup, f"config/{cfg}")
        notifier.send_message("🚨 AUTO-ROLLBACK: Reverted params due to -3% DD in early session.")
    except Exception as e: logger.error(f"Rollback FAILED: {e}")

# 3. TRADE JOURNAL CONFIGURATION
JOURNAL_FILE = "trade_journal_v3_ws.csv"
JOURNAL_HEADERS = ['date', 'time', 'symbol', 'strategy', 'pattern', 'direction', 'entry', 'sl', 'target', 'exit_price', 'exit_type', 'pnl', 'r_multiple', 'confidence', 'score', 'bars_held']

# SECTOR RISK MAP
SECTOR_RISK = {
    "NIFTY_BANK": {"target_pct": 0.012, "sl_pct": 0.006, "label": "BANK"},
    "NIFTY_IT": {"target_pct": 0.010, "sl_pct": 0.005, "label": "IT"},
    "NIFTY_AUTO": {"target_pct": 0.015, "sl_pct": 0.008, "label": "AUTO"},
    "NIFTY_ENERGY": {"target_pct": 0.014, "sl_pct": 0.0065, "label": "ENERGY"},
    "NIFTY_METAL": {"target_pct": 0.020, "sl_pct": 0.010, "label": "METAL"},
}
DEFAULT_RISK = {"target_pct": 0.010, "sl_pct": 0.005, "label": "STANDARD"}

def get_params(symbol, sector):
    return SECTOR_RISK.get(sector, DEFAULT_RISK)

def write_trade_to_journal(trade_info: dict):
    file_exists = os.path.exists(JOURNAL_FILE)
    try:
        with open(JOURNAL_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=JOURNAL_HEADERS, extrasaction='ignore')
            if not file_exists: writer.writeheader()
            writer.writerow(trade_info)
    except Exception as e: logger.error(f"JOURNAL ERROR: {e}")

def load_config():
    if not os.path.exists("config/paper_mode.yaml"): return {"mode": "PAPER"}
    with open("config/paper_mode.yaml", "r") as f: return yaml.safe_load(f)

def save_active_trades(trades):
    try:
        save_data = {k: (v.to_dict() if isinstance(v, ManagedTrade) else v) for k, v in trades.items()}
        with open("active_trades_v3.json", "w") as f: json.dump(save_data, f, indent=2, default=str)
    except Exception as e: logger.error(f"STATE ERROR: {e}")

def load_active_trades():
    if not os.path.exists("active_trades_v3.json"): return {}
    try:
        with open("active_trades_v3.json", "r") as f:
            loaded = json.load(f)
            return {k: ManagedTrade.from_dict(v) for k, v in loaded.items() if isinstance(v, dict) and 'original_sl' in v}
    except Exception as e: return {}

# === PER-STOCK VOLATILITY FILTER START ===
# REVERT: Comment out this function to disable per-stock volatility check
def is_stock_tradeable(df_stock: pd.DataFrame) -> tuple:
    """Quick per-stock vol check BEFORE running expensive strategy engines."""
    # Safety: If less than 2 bars, skip filter to avoid index error
    if len(df_stock) < 2:
        return (True, "NORMAL")
        
    # Uses previous bar (iloc[-2]) to avoid look-ahead bias
    latest = df_stock.iloc[-2]
    range_pct = ((latest['High'] - latest['Low']) / latest['Close']) * 100
    
    # Too quiet — stock isn't moving enough to trade
    if range_pct < 0.5:
        return (False, "DEAD_STOCK")  # Skip: no opportunity
    
    # Too wild — stock is in event-driven chaos (use wider SL)
    if range_pct > 4.0:
        return (True, "HIGH_VOL_STOCK")  # Trade but widen SL to 1.0× ATR
    
    return (True, "NORMAL")
# === PER-STOCK VOLATILITY FILTER END ===

def scan_symbol(args):
    symbol, token, data_reader, sel, regime_gate, vix_filter = args
    try:
        df_5m = data_reader.get_5m_candles(token, 100)
        if df_5m is not None and not df_5m.empty:
            # === PER-STOCK VOLATILITY FILTER START ===
            # REVERT: Comment out this check to disable per-stock filtering
            tradeable, stock_vol = is_stock_tradeable(df_5m)
            if not tradeable:
                return None
            # === PER-STOCK VOLATILITY FILTER END ===

            best_sig = sel.select_best(df_5m, symbol)
            if best_sig and regime_gate.is_strategy_allowed(best_sig.strategy_name):
                adj = regime_gate.get_confidence_adjustment(best_sig.strategy_name)
                final_conf = best_sig.confidence_pct + adj
                
                # === VIX FILTER START ===
                # REVERT: Comment out this block to disable VIX directional bias
                adjusted_conf, vix_allowed, vix_reason = vix_filter.filter_signal(
                    best_sig.direction, final_conf
                )
                if not vix_allowed:
                    return None
                final_conf = adjusted_conf
                # === VIX FILTER END ===

                if final_conf >= 60:
                    return {'sig': best_sig, 'symbol': symbol, 'token': token, 'adj_conf': final_conf, 'stock_vol': stock_vol}
    except Exception as e:
        pass # Silent error for bulk scan
    return None

def live_trader():
    logger.info("INITIALIZING LIVE TRADER V4 (Parallel Scanning + Optimized Data)")
    
    cfg = load_config()
    is_paper = cfg.get('mode', 'PAPER') == 'PAPER'
    capital_per_trade = 100000.0 
    total_capital = 1000000.0
    
    # === VIX & EVENT FILTER START ===
    # REVERT: Comment out these initializations to disable advanced filters
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    event_cal = EventCalendar("config/no_trade_dates.yaml")
    vix_token = "99926017" # INDIA VIX from broker_tokens.json
    # === VIX & EVENT FILTER END ===

    # [BOOT] Validation Print
    logger.info(f"[BOOT] Engines: [MOMENTUM, MEAN_REVERSION] | Filters: [REGIME, VIX, PER_STOCK_VOL, EVENT_CAL] | Risk: 1% | Capital: INR {total_capital:,.2f}")

    broker = AngelOneBroker()
    if not broker.login(): return
    
    data_reader = MemoryDataReader(broker)
    sel = StrategySelector()
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
    
    # SMC Engines disabled for Week 1 Paper Validation
    # Phase 2: Enable after 2 weeks paper validation
    # sel.register("SWEEP_RETEST", SweepRetestEngine(config_path="config/sweep_retest.yaml"), sweep_retest_adapter)
    # sel.register("STRUCTURE", StructureStrategyEngine(config_path="config/structure_strategy.yaml"), structure_strategy_adapter)
    
    regime_gate = RegimeGate(config_path="config/regime_gating.yaml")
    nifty_token = "99926000"
    portfolio_mgr = PortfolioManager()
    tsl_manager = TrailingSLManager(config_path="config/trailing_sl.yaml")
    equity_tracker = EquityTracker()
    notifier = TelegramNotifier()
    
    check_auto_rollback()

    # Load Universe
    try:
        with open("config/universe_full.yaml", "r") as f: universe = yaml.safe_load(f)['universe']
        with open("broker_tokens_full.json", "r") as f: token_map = json.load(f)
        symbols = list(universe['mappings'].keys())
        init_map = {s: str(token_map[f"{s}-EQ"]) for s in symbols if f"{s}-EQ" in token_map}
        tier1_symbols = universe['tiers'].get('TIER_1', [])
        data_reader.initialize_data(init_map, tier1_symbols=tier1_symbols)
        data_reader.start_streaming(list(init_map.values()))
    except Exception as e:
        logger.error(f"CONFIG ERROR: {e}")
        return

    logger.info("WARM-UP: Awaiting data stream...")
    time.sleep(10)

    active_trades = load_active_trades()
    last_heartbeat = time.time()
    last_5m_boundary = None
    regime_tracker = []

    # Parallel Scanning Pool
    executor = ThreadPoolExecutor(max_workers=20)

    try:
        while True:
            now = datetime.now()
            curr_time = now.time()
            market_close = datetime.strptime("15:30:00", "%H:%M:%S").time()
            entry_stop = datetime.strptime("14:30:00", "%H:%M:%S").time()
            market_open = datetime.strptime("09:15:00", "%H:%M:%S").time()
            current_5m = (now.minute // 5) * 5

            if curr_time >= market_close or now.weekday() >= 5: # 5=Sat, 6=Sun
                if now.weekday() >= 5:
                    logger.info("WEEKEND: System in idle mode. NSE Market Closed.")
                    # On weekends, we just exit once, or sleep. 
                    # To avoid launcher restart loops, let's just sleep until Monday 09:00.
                    time.sleep(3600); continue 

                logger.info("MARKET CLOSED. Force-closing all positions...")
                for t_key in list(active_trades.keys()):
                    trade = active_trades[t_key]
                    live_tick = data_reader.get_live_price(init_map.get(trade.symbol))
                    exit_price = live_tick['ltp'] if live_tick else trade.entry_price
                    exits = tsl_manager.force_close(trade, exit_price)
                    for ev in exits:
                        write_trade_to_journal({'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S'), 'symbol': trade.symbol, 'strategy': trade.strategy, 'direction': trade.direction, 'entry': trade.entry_price, 'exit_price': ev['price'], 'exit_type': ev['type'], 'pnl': ev['pnl']})
                    portfolio_mgr.on_trade_closed(t_key, trade.total_pnl)
                    del active_trades[t_key]
                
                save_active_trades(active_trades)
                reporter = DailyReportGenerator(journal_path=JOURNAL_FILE)
                report = reporter.generate_daily_report(regime_logs=regime_tracker)
                if report and report.get('total_trades', 0) > 0:
                    win_count = int(report.get('win_rate', 0) / 100 * report.get('closed', 0))
                    equity_tracker.record_day(
                        date=report['date'], 
                        pnl=report.get('net_pnl', 0.0), 
                        trades_closed=report.get('closed', 0), 
                        win_count=win_count
                    )
                    notifier.send_message(reporter.format_telegram_message(report))
                break
            
            if curr_time < market_open:
                portfolio_mgr.on_day_reset()
                time.sleep(10); continue

            # --- AUTO ROLLBACK ---
            global ROLLBACK_MONITORING, ROLLBACK_DEADLINE
            if ROLLBACK_MONITORING:
                if now > ROLLBACK_DEADLINE: ROLLBACK_MONITORING = False
                elif portfolio_mgr.get_portfolio_summary()['daily_pnl'] < -(total_capital * 0.03):
                    perform_rollback(notifier); ROLLBACK_MONITORING = False

            # 1. REGIME UPDATE
            if current_5m != last_5m_boundary:
                df_nifty = data_reader.get_5m_candles(nifty_token, 50)
                if df_nifty is not None:
                    regime = regime_gate.update_regime(df_nifty)
                    regime_tracker.append(regime); logger.info(f"[REGIME] {regime}")

            # 2. EXIT MONITORING (High Frequency)
            active_symbols = list(set([k.split('_')[0] for k in active_trades.keys()]))
            for symbol in active_symbols:
                token = init_map.get(symbol)
                live_tick = data_reader.get_live_price(token)
                if live_tick:
                    trade_keys = [k for k in active_trades.keys() if k.startswith(symbol)]
                    for tk in trade_keys:
                        trade = active_trades[tk]
                        events = tsl_manager.check_exits(trade, live_tick['ltp'], live_tick['ltp'], live_tick['ltp'])
                        for ev in events:
                            write_trade_to_journal({'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S'), 'symbol': symbol, 'strategy': trade.strategy, 'direction': trade.direction, 'entry': trade.entry_price, 'exit_price': ev['price'], 'exit_type': ev['type'], 'pnl': ev['pnl']})
                            notifier.send_message(f"🔴 EXIT {symbol}: {ev['type']} @ {ev['price']:.2f} (PnL: {ev['pnl']:.2f})")
                        if trade.is_closed:
                            portfolio_mgr.on_trade_closed(tk, trade.total_pnl)
                            del active_trades[tk]; save_active_trades(active_trades)

    # 3. ENTRY SCANNING (Parallel)
            if curr_time < entry_stop and current_5m != last_5m_boundary:
                # === EVENT CALENDAR START ===
                # REVERT: Comment out this block to disable event calendar blocking
                today_str = now.strftime('%Y-%m-%d')
                if not event_cal.should_allow_entries(today_str):
                    if current_5m != last_5m_boundary: # Send only once per 5m
                        logger.info(f"EVENT CALENDAR: {today_str} is blocked. Staying flat.")
                        notifier.send_message(f"EVENT ALERT: Today is {event_cal.get_reason(today_str)}. Bot is in MONITOR-ONLY mode.")
                    last_5m_boundary = current_5m
                    continue
                # === EVENT CALENDAR END ===

                # === VIX UPDATE START ===
                # REVERT: Comment out this block to disable VIX updates
                df_vix = data_reader.get_5m_candles(vix_token, 20)
                vix_filter.update(df_vix)
                # === VIX UPDATE END ===

                logger.info(f"Starting Parallel Scan for {len(symbols)} stocks...")
                scan_args = [(s, init_map[s], data_reader, sel, regime_gate, vix_filter) for s in symbols if s in init_map]
                results = list(executor.map(scan_symbol, scan_args))
                candidate_signals = [r for r in results if r is not None]
                
                if candidate_signals:
                    candidate_signals.sort(key=lambda x: (-x['adj_conf']))
                    slots = regime_gate.get_max_positions() - len(active_trades)
                    for item in candidate_signals:
                        if slots <= 0: break
                        t_key = f"{item['symbol']}_{item['sig'].strategy_name}"
                        if t_key not in active_trades:
                            sector = universe['mappings'][item['symbol']].get('sector', 'UNKNOWN')
                            params = get_params(item['symbol'], sector)
                            entry = item['sig'].entry
                            sl = entry - (entry * params['sl_pct']) if item['sig'].direction == 'CE' else entry + (entry * params['sl_pct'])
                            can_trade, reason = portfolio_mgr.can_take_trade(item['symbol'], item['sig'].direction, capital_per_trade)
                            if can_trade:
                                active_trades[t_key] = tsl_manager.create_trade(item['symbol'], item['sig'].direction, entry, sl, int(capital_per_trade/entry), item['sig'].strategy_name)
                                portfolio_mgr.on_trade_opened(t_key, item['symbol'], item['sig'].direction, capital_per_trade)
                                slots -= 1; save_active_trades(active_trades)
                                notifier.send_message(f"✅ ENTRY: {item['symbol']} ({item['sig'].strategy_name}) @ {entry:.2f}")
                
                last_5m_boundary = current_5m
                logger.info("Scan Complete.")

            time.sleep(1)
    except Exception as e: logger.error(f"CRITICAL ERROR: {e}")
    finally:
        executor.shutdown()
        data_reader.ws_manager.stop()
        logger.info("Bot Offline.")

if __name__ == "__main__":
    live_trader()
