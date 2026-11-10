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

# 1. LOGGING CONFIGURATION
logging.basicConfig(
    filename='logs/live_trader_output.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('live_trader')

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
logger.addHandler(console_handler)

# 2. TRADE JOURNAL CONFIGURATION
JOURNAL_FILE = "trade_journal_multi_strategy.csv"
JOURNAL_HEADERS = [
    'date', 'time', 'symbol', 'strategy', 'pattern', 'direction',
    'entry', 'sl', 'target', 'exit_price', 'exit_type', 'pnl',
    'r_multiple', 'confidence', 'score', 'bars_held'
]

def write_trade_to_journal(trade_info: dict):
    """Append a single trade to the CSV journal. Creates file with headers if it doesn't exist."""
    file_exists = os.path.exists(JOURNAL_FILE)
    try:
        with open(JOURNAL_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=JOURNAL_HEADERS, extrasaction='ignore')
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade_info)
        logger.info(f"JOURNAL: Trade written to {JOURNAL_FILE}")
    except Exception as e:
        logger.error(f"JOURNAL ERROR: Failed to write to {JOURNAL_FILE}: {e}")

def load_config():
    with open("config/paper_mode.yaml", "r") as f:
        return yaml.safe_load(f)

# Persistence Helpers
def save_active_trades(trades):
    try:
        save_data = {}
        for k, v in trades.items():
            if isinstance(v, ManagedTrade):
                save_data[k] = v.to_dict()
            else:
                save_data[k] = v

        with open("active_trades.json", "w") as f:
            json.dump(save_data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"STATE ERROR: Failed to save active trades: {e}")

def load_active_trades():
    active_trades = {}
    if os.path.exists("active_trades.json"):
        try:
            with open("active_trades.json", "r") as f:
                loaded = json.load(f)
                
                # FIX 3: Filter out MANUAL trades
                for k, v in loaded.items():
                    if isinstance(v, dict) and (v.get("setup") == "MANUAL_RECOVERY" or v.get("setup") == "MANUAL_EXIT"):
                        logger.warning(f"BLOCK: Manual trade {k} ignored. System-only mode enforced.")
                        continue
                    
                    if isinstance(v, dict) and 'original_sl' in v:
                        active_trades[k] = ManagedTrade.from_dict(v)
                    else:
                        active_trades[k] = v
                    
                logger.info(f"INIT: Resumed {len(active_trades)} active trades from state file.")
                return active_trades
        except Exception as e:
            logger.error(f"STATE ERROR: Failed to load active trades: {e}")
            return {}
    return {}

def live_trader():
    logger.info("INITIALIZING LIVE TRADER V4 (Multi-Strategy Framework)")
    
    cfg = load_config()
    is_paper = cfg['mode'] == 'PAPER'
    
    # Initialize Multi-Strategy Framework
    sel = StrategySelector()
    momentum_engine = MomentumBreakoutEngine()
    mean_reversion_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    
    # Initialize Trailing SL Manager
    tsl_manager = TrailingSLManager(config_path="config/trailing_sl.yaml")
    
    sel.register("MOMENTUM", momentum_engine, momentum_adapter)
    sel.register("MEAN_REVERSION", mean_reversion_engine, mean_reversion_adapter)
    
    # Initialize Notifier
    notifier = TelegramNotifier()
    notifier.send_message(f"Trading Bot Online\nMode: {'PAPER' if is_paper else 'LIVE'}\nTime: {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. Login
    broker = AngelOneBroker()
    if not broker.login():
        logger.error("LOGIN FAILED: Shutting down.")
        return

    # 2. Setup Components
    feed_manager = IntermarketFeedManager()
    
    # 3. Load Symbols from universe.yaml
    try:
        with open("config/universe.yaml", "r") as f:
            universe = yaml.safe_load(f)['universe']
        symbols = list(universe['mappings'].keys())
    except Exception as e:
        logger.error(f"CONFIG ERROR: Could not load symbols: {e}")
        return
    
    # Load Tokens
    try:
        with open("broker_tokens.json", "r") as f:
            token_map = json.load(f)
    except Exception as e:
        logger.error(f"CONFIG ERROR: Could not load tokens: {e}")
        return

    # Bot State
    active_trades = load_active_trades()
    total_scans = 0
    total_errors = 0
    trades_opened_today = 0
    trades_closed_today = 0
    last_heartbeat = time.time()

    logger.info(f"BOT: Paper Mode={is_paper} | Scanning {len(symbols)} stocks with Momentum + Mean Reversion")
    
    while True:
        now = datetime.now()
        curr_time = now.time()
        
        # MARKET OPEN CHECK (9:20 AM - 3:30 PM)
        market_close = datetime.strptime("15:30:00", "%H:%M:%S").time()
        entry_stop = datetime.strptime("14:30:00", "%H:%M:%S").time()
        market_open = datetime.strptime("09:15:00", "%H:%M:%S").time()
        
        if curr_time >= market_close:
            logger.info("=" * 60)
            logger.info("MARKET CLOSED: 03:30 PM - Executing Shutdown Summary")
            logger.info(f"Total Scans: {total_scans}")
            logger.info(f"Total Errors: {total_errors}")
            logger.info(f"Trades Opened Today: {trades_opened_today}")
            logger.info(f"Trades Closed Today: {trades_closed_today}")
            logger.info(f"Active Trades at Close: {len(active_trades)}")

            # Force close all at market end
            for t_key, trade in list(active_trades.items()):
                if isinstance(trade, ManagedTrade) and not trade.is_closed:
                    force_exits = tsl_manager.force_close(trade, current_price)
                    for event in force_exits:
                        write_trade_to_journal({
                            'date': now.strftime('%Y-%m-%d'),
                            'time': now.strftime('%H:%M:%S'),
                            'symbol': trade.symbol,
                            'strategy': trade.strategy,
                            'pattern': trade.pattern,
                            'direction': trade.direction,
                            'entry': trade.entry_price,
                            'exit_price': event['price'],
                            'exit_type': 'MARKET_CLOSE',
                            'pnl': event['pnl'],
                            'r_multiple': event['r_multiple'],
                            'qty_exited': event['qty'],
                            'qty_remaining': 0,
                        })
            
            logger.info("=" * 60)
            logger.info("Bot shutdown complete.")
            notifier.send_message(f"Market Closed\nTime: {now.strftime('%H:%M:%S')}")
            break
            
        if curr_time < market_open:
            time.sleep(60)
            continue

        # 1. Heartbeat Logic (Every 30 mins)
        if time.time() - last_heartbeat > 1800:
            last_heartbeat = time.time()
            notifier.send_message(f"Bot Heartbeat\nScans: {total_scans}\nStatus: Healthy")

        for symbol in symbols:
            try:
                total_scans += 1
                angel_sym = f"{symbol}-EQ"
                token = token_map.get(angel_sym)
                if not token: continue

                # A. Fetch Live Data
                df_1m = broker.get_historical_data(angel_sym, token, interval="ONE_MINUTE", days=2)
                if df_1m is None or df_1m.empty: continue

                # Resample to 5m
                df_5m = PriceActionEngine.resample_data(df_1m, '5min')
                if df_5m.empty: continue

                current_price = df_5m['Close'].iloc[-1]

                # B. MONITOR ACTIVE TRADES — Check exits using TSL Manager
                trade_keys_to_remove = []
                for t_key in list(active_trades.keys()):
                    if not t_key.startswith(symbol):
                        continue

                    trade = active_trades[t_key]

                    # Handle both old dict format and new ManagedTrade format
                    if isinstance(trade, dict):
                        # Legacy trade from active_trades.json — convert to ManagedTrade
                        trade = ManagedTrade.from_dict(trade)
                        active_trades[t_key] = trade

                    if trade.is_closed:
                        trade_keys_to_remove.append(t_key)
                        continue

                    # Get candle high/low/close for accurate exit detection
                    current_high = float(df_5m['High'].iloc[-1]) if 'High' in df_5m.columns else current_price
                    current_low = float(df_5m['Low'].iloc[-1]) if 'Low' in df_5m.columns else current_price

                    # Check for exits (partial or full)
                    exit_events = tsl_manager.check_exits(trade, current_high, current_low, current_price)

                    for event in exit_events:
                        # Log each exit event to the journal
                        write_trade_to_journal({
                            'date': now.strftime('%Y-%m-%d'),
                            'time': now.strftime('%H:%M:%S'),
                            'symbol': trade.symbol,
                            'strategy': trade.strategy,
                            'pattern': trade.pattern,
                            'direction': trade.direction,
                            'entry': trade.entry_price,
                            'sl': trade.current_sl,
                            'target': event['price'],
                            'exit_price': event['price'],
                            'exit_type': event['type'],
                            'pnl': event['pnl'],
                            'r_multiple': event['r_multiple'],
                            'confidence': trade.confidence,
                            'score': trade.score,
                            'bars_held': '',
                            'qty_exited': event['qty'],
                            'qty_remaining': trade.remaining_qty,
                        })

                        # Send Telegram notification for each exit
                        try:
                            notifier.send_message(
                                f"{'🎯 TARGET' if 'PARTIAL' in event['type'] else '🛑 SL'} | "
                                f"{trade.symbol} {trade.direction} | "
                                f"{event['type']} | Qty={event['qty']} @ {event['price']:.2f} | "
                                f"PnL={event['pnl']:+.2f} | Remaining={trade.remaining_qty}"
                            )
                        except Exception:
                            pass

                        # Log to meta_db
                        try:
                            meta_log({
                                'symbol': trade.symbol,
                                'date': now.strftime('%Y-%m-%d'),
                                'direction': trade.direction,
                                'strategy': trade.strategy,
                                'entry': trade.entry_price,
                                'sl': trade.current_sl,
                                'target': event['price'],
                                'qty': event['qty'],
                                'outcome': event['type'],
                                'pnl': event['pnl'],
                                'score': trade.score,
                            })
                        except Exception:
                            pass

                    # If trade is fully closed, mark for removal
                    if trade.is_closed:
                        trade_keys_to_remove.append(t_key)
                        trades_closed_today += 1

                if trade_keys_to_remove:
                    for k in trade_keys_to_remove: 
                        if k in active_trades: del active_trades[k]
                    save_active_trades(active_trades) # Update persistence

                # C. Entry Signal (Stop entries after 2:30 PM)
                if curr_time < entry_stop:
                    # Final Decision using Multi-Strategy Framework (Slice last 100 bars)
                    df_slice = df_5m.tail(100)
                    
                    # FIX 4: Momentum Diagnostic Logging
                    try:
                        mom_res = momentum_engine.generate_signal(df_slice, symbol)
                        if mom_res and mom_res.get('signal'):
                            logger.info(f"MOM_DIAG {symbol}: Signal detected, Score={mom_res.get('score')}")
                    except Exception as e:
                        logger.debug(f"MOM_DIAG {symbol}: scan failed: {e}")

                    best_sig = sel.select_best(df_slice, symbol)

                    if best_sig:
                        # Log EVERY detected signal
                        logger.info(
                            f"SIGNAL: {symbol} | Strategy={best_sig.strategy_name} | "
                            f"Pattern={best_sig.setup_type} | Direction={best_sig.direction} | "
                            f"Score={best_sig.score} | Confidence={best_sig.confidence_pct}% | "
                            f"Entry={best_sig.entry} | SL={best_sig.sl} | Target={best_sig.target1}"
                        )

                        if best_sig.confidence_pct >= 60:
                            trade_key = f"{symbol}_{best_sig.strategy_name}"
                            
                            if trade_key not in active_trades and len(active_trades) < 3:
                                logger.info(f"ORDER TRIGGERED: {symbol} | Strategy={best_sig.strategy_name} | Setup={best_sig.setup_type}")
                                
                                # Calculate Qty based on 1% risk
                                dist = abs(best_sig.entry - best_sig.sl)
                                qty = 1
                                if dist > 0:
                                    capital = 1000000.0 # Standard base
                                    risk_amt = capital * 0.01
                                    qty = int(risk_amt / dist)
                                    if qty <= 0: qty = 1

                                trade_info = {
                                    'date': now.strftime('%Y-%m-%d'),
                                    'time': now.strftime('%H:%M:%S'),
                                    'symbol': symbol, 
                                    'direction': best_sig.direction,
                                    'entry': best_sig.entry, 
                                    'sl': best_sig.sl,
                                    'target': best_sig.target1, 
                                    'qty': qty,
                                    'start_time': now, 
                                    'setup': best_sig.setup_type,
                                    'pattern': best_sig.setup_type,
                                    'score': best_sig.score, 
                                    'strategy': best_sig.strategy_name,
                                    'confidence': best_sig.confidence_pct
                                }

                                if is_paper:
                                    logger.info(f"PAPER ORDER: {best_sig.direction} {qty} shares of {symbol} at {best_sig.entry}")
                                    managed_trade = tsl_manager.create_trade(
                                        symbol=symbol,
                                        direction=best_sig.direction,
                                        entry_price=best_sig.entry,
                                        sl_price=best_sig.sl,
                                        original_qty=qty,
                                        strategy=best_sig.strategy_name,
                                        pattern=best_sig.setup_type,
                                        score=best_sig.score,
                                        confidence=best_sig.confidence_pct,
                                    )
                                    active_trades[trade_key] = managed_trade
                                    save_active_trades(active_trades)
                                    write_trade_to_journal(trade_info) # Record entry
                                else:
                                    side = 'BUY' if best_sig.direction == 'CE' else 'SELL'
                                    broker.place_bracket_order(
                                        symbol=angel_sym, token=token, qty=qty,
                                        side=side, entry_price=best_sig.entry,
                                        sl_price=best_sig.sl, target_price=best_sig.target1
                                    )
                                    managed_trade = tsl_manager.create_trade(
                                        symbol=symbol,
                                        direction=best_sig.direction,
                                        entry_price=best_sig.entry,
                                        sl_price=best_sig.sl,
                                        original_qty=qty,
                                        strategy=best_sig.strategy_name,
                                        pattern=best_sig.setup_type,
                                        score=best_sig.score,
                                        confidence=best_sig.confidence_pct,
                                    )
                                    active_trades[trade_key] = managed_trade
                                    save_active_trades(active_trades)
                                    write_trade_to_journal(trade_info) # Record entry
                                
                                trades_opened_today += 1
                                notifier.notify_trade("ENTRY", {
                                    "symbol": symbol, "direction": best_sig.direction,
                                    "price": best_sig.entry, "strategy": best_sig.strategy_name,
                                    "size": qty, "score": best_sig.score,
                                    "regime": "NORMAL", "rr": best_sig.target_r
                                })
                        else:
                            logger.info(f"REJECTED: {symbol} | Confidence {best_sig.confidence_pct}% < 60% threshold")
                            try:
                                # Send as plain text to avoid Markdown parsing errors
                                notifier.send_message(
                                    f"SIGNAL REJECTED\n"
                                    f"Symbol: {symbol}\n"
                                    f"Strategy: {best_sig.strategy_name}\n"
                                    f"Score: {best_sig.score}\n"
                                    f"Confidence: {best_sig.confidence_pct}% (Threshold: 60%)"
                                )
                            except Exception:
                                pass

                time.sleep(0.5) # Rate limit

            except Exception as e:
                total_errors += 1
                logger.error(f"SCAN ERROR: {symbol} | {type(e).__name__}: {e}")
                if "AB1021" in str(e):
                    time.sleep(2) # Extra backoff on rate limit

        time.sleep(60) # Increased from 30 to reduce API load

if __name__ == "__main__":
    live_trader()
