import os
import time
import json
import yaml
import pandas as pd
import logging
import csv
from datetime import datetime
from modules.price_action_engine import PriceActionEngine
from modules.broker_layer import AngelOneBroker
from modules.intermarket.feeds.manager import IntermarketFeedManager
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from meta_learning.tracker import log_trade as meta_log
from notification.telegram_notifier import TelegramNotifier
from modules.trailing_sl_manager import TrailingSLManager, ManagedTrade
from modules.data.redis_data_reader import RedisDataReader

# 1. LOGGING CONFIGURATION
logging.basicConfig(
    filename='logs/live_trader_output.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('live_trader')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
logger.addHandler(console_handler)

# 2. TRADE JOURNAL CONFIGURATION
JOURNAL_FILE = "trade_journal_multi_strategy.csv"
JOURNAL_HEADERS = ['date', 'time', 'symbol', 'strategy', 'pattern', 'direction', 'entry', 'sl', 'target', 'exit_price', 'exit_type', 'pnl', 'r_multiple', 'confidence', 'score', 'bars_held']

# SECTOR RISK MAP (Golden Cheat Sheet)
SECTOR_RISK = {
    "NIFTY_BANK": {"target_pct": 0.012, "sl_pct": 0.006, "label": "BANK"},
    "NIFTY_IT": {"target_pct": 0.010, "sl_pct": 0.005, "label": "IT"},
    "NIFTY_FMCG": {"target_pct": 0.007, "sl_pct": 0.004, "label": "FMCG"},
    "NIFTY_AUTO": {"target_pct": 0.015, "sl_pct": 0.008, "label": "AUTO"},
    "NIFTY_ENERGY": {"target_pct": 0.014, "sl_pct": 0.0065, "label": "ENERGY"},
    "NIFTY_METAL": {"target_pct": 0.020, "sl_pct": 0.010, "label": "METAL"},
    "NIFTY_FINSERV": {"target_pct": 0.025, "sl_pct": 0.012, "label": "HIGH_VOL"},
    "HIGH_VOL": {"target_pct": 0.025, "sl_pct": 0.012, "label": "HIGH_VOL"},
}
DEFAULT_RISK = {"target_pct": 0.010, "sl_pct": 0.005, "label": "STANDARD"}

def get_params(symbol, sector):
    if symbol in ["ADANIENT", "ADANIPORTS", "BAJFINANCE"]:
        return SECTOR_RISK["HIGH_VOL"]
    return SECTOR_RISK.get(sector, DEFAULT_RISK)

def write_trade_to_journal(trade_info: dict):
    file_exists = os.path.exists(JOURNAL_FILE)
    try:
        with open(JOURNAL_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=JOURNAL_HEADERS, extrasaction='ignore')
            if not file_exists: writer.writeheader()
            writer.writerow(trade_info)
        logger.info(f"JOURNAL: Trade written to {JOURNAL_FILE}")
    except Exception as e: logger.error(f"JOURNAL ERROR: {e}")

def load_config():
    with open("config/paper_mode.yaml", "r") as f:
        return yaml.safe_load(f)

def save_active_trades(trades):
    try:
        save_data = {k: (v.to_dict() if isinstance(v, ManagedTrade) else v) for k, v in trades.items()}
        with open("active_trades.json", "w") as f: json.dump(save_data, f, indent=2, default=str)
    except Exception as e: logger.error(f"STATE ERROR: {e}")

def load_active_trades():
    if not os.path.exists("active_trades.json"): return {}
    try:
        with open("active_trades.json", "r") as f:
            loaded = json.load(f)
            return {k: ManagedTrade.from_dict(v) for k, v in loaded.items() if isinstance(v, dict) and 'original_sl' in v}
    except Exception as e:
        logger.error(f"STATE ERROR: {e}")
        return {}

def live_trader():
    logger.info("INITIALIZING LIVE TRADER V4 (Production Scaled)")
    
    cfg = load_config()
    is_paper = cfg['mode'] == 'PAPER'
    max_pos = 10 # HARD LIMIT UPGRADED
    capital_per_trade = 100000.0 # Fixed Capital per Trade
    
    sel = StrategySelector()
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
    
    tsl_manager = TrailingSLManager(config_path="config/trailing_sl.yaml")
    notifier = TelegramNotifier()
    notifier.send_message(f"Bot Online | Scaled Mode | MaxPos: {max_pos}")
    
    broker = AngelOneBroker()
    if not broker.login(): return
    redis_reader = RedisDataReader()

    # Load Full Universe
    try:
        u_path = "config/universe_full.yaml" if os.path.exists("config/universe_full.yaml") else "config/universe.yaml"
        with open(u_path, "r") as f:
            universe = yaml.safe_load(f)['universe']
        symbols = list(universe['mappings'].keys())
        
        t_path = "broker_tokens_full.json" if os.path.exists("broker_tokens_full.json") else "broker_tokens.json"
        with open(t_path, "r") as f:
            token_map = json.load(f)
    except Exception as e:
        logger.error(f"CONFIG ERROR: {e}")
        return

    # WARM-UP
    logger.info("WARM-UP: Awaiting data for Tier 1...")
    while True:
        ready = sum(1 for s in universe['tiers']['TIER_1'] if redis_reader.get_candle_count(token_map.get(f"{s}-EQ"), '5m') >= 20)
        pct = (ready / len(universe['tiers']['TIER_1'])) * 100
        if pct >= 80: break
        logger.info(f"WARM-UP: Tier 1 ready {pct:.1f}%")
        time.sleep(30)

    active_trades = load_active_trades()
    last_heartbeat = time.time()
    last_5m_boundary = None
    last_15m_boundary = None

    while True:
        now = datetime.now()
        curr_time = now.time()
        market_close = datetime.strptime("15:30:00", "%H:%M:%S").time()
        entry_stop = datetime.strptime("14:30:00", "%H:%M:%S").time()
        market_open = datetime.strptime("09:15:00", "%H:%M:%S").time()

        if curr_time >= market_close:
            # Force close logic (similar to v1 but using Redis)
            logger.info("MARKET CLOSED. Shutting down.")
            break
        if curr_time < market_open:
            time.sleep(60); continue

        # Heartbeat
        if time.time() - last_heartbeat > 1800:
            last_heartbeat = time.time()
            notifier.send_message(f"Heartbeat | Active: {len(active_trades)} | Redis: {redis_reader.is_connected}")

        # Tiered Scanning Gates
        current_5m = (now.minute // 5) * 5
        current_15m = (now.minute // 15) * 15
        is_5m_boundary = (current_5m != last_5m_boundary)
        is_15m_boundary = (current_15m != last_15m_boundary)

        cycle_start = time.time()
        candidate_signals = []

        # VOLATILITY ADJUSTMENT (NIFTY)
        vol_mult = 1.0
        nifty_df = redis_reader.get_5m_candles("26000", 20)
        if nifty_df is not None and not nifty_df.empty:
            day_open = nifty_df['Open'].iloc[0]
            day_high = nifty_df['High'].max()
            day_low = nifty_df['Low'].min()
            nifty_range_pct = (day_high - day_low) / day_open * 100
            if nifty_range_pct > 0.8: vol_mult = 1.3
            elif nifty_range_pct < 0.4: vol_mult = 0.7
            logger.info(f"NIFTY RANGE: {nifty_range_pct:.2f}% | VOL_MULT: {vol_mult}")

        for symbol in symbols:
            try:
                angel_sym = f"{symbol}-EQ"
                token = token_map.get(angel_sym)
                if not token: continue

                tier = universe['mappings'][symbol].get('tier', 3)
                
                # A. EXIT MONITORING (Every 5s for all active trades)
                if any(t_key.startswith(symbol) for t_key in active_trades):
                    df_5m = redis_reader.get_5m_candles(token, 100)
                    if df_5m is not None:
                        live_tick = redis_reader.get_live_price(token)
                        current_price = float(live_tick['ltp']) if live_tick else float(df_5m['Close'].iloc[-1])
                        
                        trade = next(v for k, v in active_trades.items() if k.startswith(symbol))
                        live_c = redis_reader.get_live_candle(token, '5m')
                        c_high = max(float(df_5m['High'].iloc[-1]), float(live_c.get('high', 0))) if live_c else float(df_5m['High'].iloc[-1])
                        c_low = min(float(df_5m['Low'].iloc[-1]), float(live_c.get('low', float('inf')))) if live_c else float(df_5m['Low'].iloc[-1])
                        
                        events = tsl_manager.check_exits(trade, c_high, c_low, current_price)
                        for ev in events:
                            write_trade_to_journal({'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S'), 'symbol': symbol, 'strategy': trade.strategy, 'exit_price': ev['price'], 'exit_type': ev['type'], 'pnl': ev['pnl']})
                            notifier.send_message(f"EXIT {symbol}: {ev['type']} @ {ev['price']:.2f}")
                        if trade.is_closed:
                            del active_trades[f"{symbol}_{trade.strategy}"]
                            save_active_trades(active_trades)

                # B. ENTRY SCANNING (Tiered Frequency)
                if curr_time < entry_stop:
                    should_scan = False
                    if tier in [1, 2] and is_5m_boundary: should_scan = True
                    elif tier == 3 and is_15m_boundary: should_scan = True
                    
                    if should_scan:
                        df_5m = redis_reader.get_5m_candles(token, 100)
                        if df_5m is not None:
                            best_sig = sel.select_best(df_5m, symbol)
                            if best_sig and best_sig.confidence_pct >= 60:
                                candidate_signals.append({'sig': best_sig, 'tier': tier, 'symbol': symbol, 'token': token, 'angel_sym': angel_sym})

            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

        # C. SIGNAL RANKING & EXECUTION
        if candidate_signals:
            # Sort: Tier ASC (1 is best), Confidence DESC, Score DESC
            candidate_signals.sort(key=lambda x: (x['tier'], -x['sig'].confidence_pct, -x['sig'].score))
            
            slots_available = max_pos - len(active_trades)
            
            # Handle Signals
            for item in candidate_signals:
                sig = item['sig']
                trade_key = f"{item['symbol']}_{sig.strategy_name}"
                
                # Fetch Sector Params
                sector = universe['mappings'][item['symbol']].get('sector', 'UNKNOWN')
                params = get_params(item['symbol'], sector)
                
                # Dynamic SL/Target Calculation (Sector Based)
                entry = sig.entry
                sl_dist = entry * params['sl_pct']
                target_dist = entry * params['target_pct'] * vol_mult
                
                # Confidence Scaling
                if sig.confidence_pct >= 75:
                    target_dist *= 1.2 # Aggressive Target
                    logger.info(f"AGGRESSIVE MODE: {item['symbol']} Target increased +20%")
                
                # Finalize SL/Target Prices
                final_sl = entry - sl_dist if sig.direction == 'CE' else entry + sl_dist
                final_target = entry + target_dist if sig.direction == 'CE' else entry - target_dist
                
                # Calculate Quantity (Fixed Capital)
                qty = int(capital_per_trade / entry)
                
                if slots_available > 0:
                    if trade_key not in active_trades:
                        # Execute
                        if is_paper:
                            active_trades[trade_key] = tsl_manager.create_trade(item['symbol'], sig.direction, entry, final_sl, qty, sig.strategy_name)
                            write_trade_to_journal({'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S'), 'symbol': item['symbol'], 'strategy': sig.strategy_name, 'direction': sig.direction, 'entry': entry, 'sl': final_sl, 'target': final_target, 'confidence': sig.confidence_pct})
                        else:
                            broker.place_bracket_order(item['angel_sym'], item['token'], qty, 'BUY' if sig.direction=='CE' else 'SELL', entry, final_sl, final_target)
                            active_trades[trade_key] = tsl_manager.create_trade(item['symbol'], sig.direction, entry, final_sl, qty, sig.strategy_name)
                        
                        active_trades[trade_key].pattern = sig.setup_type
                        active_trades[trade_key].confidence = sig.confidence_pct
                        
                        slots_available -= 1
                        save_active_trades(active_trades)
                        notifier.send_message(f"✅ ENTRY: {item['symbol']} ({sig.strategy_name}) @ {entry:.2f}\nSL: {final_sl:.2f} | T1: {final_target:.2f}\nQty: {qty} | Conf: {sig.confidence_pct}%")
                
                elif sig.confidence_pct > 75 and trade_key not in active_trades:
                    # Out of Limit High Conf Alert
                    notifier.send_message(f"🚨 OUT OF LIMIT ALERT (High Conf: {sig.confidence_pct}%)\n"
                                        f"Symbol: {item['symbol']} | {sig.strategy_name}\n"
                                        f"Entry: {entry:.2f} | Qty: {qty}\n"
                                        f"Reason: Bot at max 10 trade limit.")
                    logger.info(f"LIMIT ALERT: {item['symbol']} signal skipped (limit full)")

        if is_5m_boundary: last_5m_boundary = current_5m
        if is_15m_boundary: last_15m_boundary = current_15m
        
        elapsed = time.time() - cycle_start
        logger.info(f"SCAN CYCLE COMPLETE: {len(symbols)} stocks in {elapsed:.1f}s | Signals: {len(candidate_signals)}")
        if elapsed > 30: logger.warning("SLOW SCAN CYCLE!")
        
        time.sleep(5)

if __name__ == "__main__":
    live_trader()
