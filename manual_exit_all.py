
import os
import json
import logging
from datetime import datetime
from modules.broker_layer import AngelOneBroker
from modules.trailing_sl_manager import TrailingSLManager, ManagedTrade
import csv

# Setup logging to match bot
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('manual_exit')

def exit_all():
    logger.info("INITIATING MANUAL EXIT ALL...")
    
    # 1. Login
    broker = AngelOneBroker()
    if not broker.login():
        return

    # 2. Load State
    if not os.path.exists("active_trades.json"):
        logger.info("No active trades found.")
        return

    with open("active_trades.json", "r") as f:
        active_trades_raw = json.load(f)
    
    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    tsl_manager = TrailingSLManager(config_path="config/trailing_sl.yaml")
    
    final_results = []
    
    for key, data in active_trades_raw.items():
        trade = ManagedTrade.from_dict(data)
        logger.info(f"Exiting {trade.symbol}...")
        
        # Get LTP
        angel_sym = f"{trade.symbol}-EQ"
        token = token_map.get(angel_sym)
        res = broker.get_market_data("NSE", angel_sym, token)
        
        if res and res.get('status'):
            current_price = float(res['data']['ltp'])
            
            # Force close logic
            exit_events = tsl_manager.force_close(trade, current_price)
            
            for event in exit_events:
                # Prepare Journal Entry
                journal_entry = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'symbol': trade.symbol,
                    'strategy': trade.strategy,
                    'pattern': trade.pattern,
                    'direction': trade.direction,
                    'entry': trade.entry_price,
                    'sl': trade.current_sl,
                    'target': event['price'],
                    'exit_price': event['price'],
                    'exit_type': 'MANUAL_EXIT_ALL',
                    'pnl': event['pnl'],
                    'r_multiple': event['r_multiple'],
                    'confidence': trade.confidence,
                    'score': trade.score,
                    'bars_held': ''
                }
                final_results.append(journal_entry)
                logger.info(f"CLOSED {trade.symbol}: PnL = {event['pnl']:+.2f}")

    # 3. Write to Journal
    JOURNAL_FILE = "trade_journal_multi_strategy.csv"
    headers = ['date', 'time', 'symbol', 'strategy', 'pattern', 'direction', 'entry', 'sl', 'target', 'exit_price', 'exit_type', 'pnl', 'r_multiple', 'confidence', 'score', 'bars_held']
    
    file_exists = os.path.exists(JOURNAL_FILE)
    with open(JOURNAL_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerows(final_results)

    # 4. Clear State
    if os.path.exists("active_trades.json"):
        os.remove("active_trades.json")
    
    logger.info("ALL TRADES CLOSED. STATE CLEARED.")

if __name__ == "__main__":
    exit_all()
