import json
from datetime import datetime

with open('data/live_paper_trades.json', 'r') as f:
    trades = json.load(f)

today = "2026-05-20"
today_trades = [t for t in trades if t['opened_at'].startswith(today)]

closed_trades = [t for t in today_trades if t['status'] == 'CLOSED']
open_trades = [t for t in today_trades if t['status'] == 'OPEN']

# Filter open trades to only those that don't have a CLOSED entry
open_trade_ids = {t['trade_id'] for t in open_trades}
closed_trade_ids = {t['trade_id'] for t in closed_trades}
truly_open_ids = open_trade_ids - closed_trade_ids

truly_open_trades = [t for t in open_trades if t['trade_id'] in truly_open_ids]

total_pnl = sum(t['pnl'] for t in closed_trades)
print(f"Today's Closed P&L: {total_pnl}")
print(f"Total Closed Trades: {len(closed_trades)}")
print(f"Open Trades ({len(truly_open_trades)}):")
for t in truly_open_trades:
    print(f"  - {t['symbol']} ({t['side']}) opened at {t['opened_at']}")
