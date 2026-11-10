import json
from datetime import datetime

with open('data/live_paper_trades.json', 'r') as f:
    data = json.load(f)

nifty_trades = {}
for t in data:
    if t.get('symbol') == 'NIFTY':
        tid = t.get('trade_id')
        if tid not in nifty_trades:
            nifty_trades[tid] = t
        else:
            nifty_trades[tid].update({k: v for k, v in t.items() if v is not None})

sorted_trades = sorted(nifty_trades.values(), key=lambda x: x.get('opened_at', ''))

print('| Trade ID | Entry Time (IST) | Exit Time (IST) | Side | Qty | Entry Px | Exit Px | P&L |')
print('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |')
for t in sorted_trades:
    entry_ts = t.get('opened_at', 'N/A')
    exit_ts = t.get('closed_at', 'OPEN')
    entry_ts_str = entry_ts.replace('T', ' ')[:19] if entry_ts != 'N/A' else 'N/A'
    exit_ts_str = exit_ts.replace('T', ' ')[:19] if exit_ts != 'OPEN' else 'OPEN'
    
    print(f"| {t.get('trade_id')} | {entry_ts_str} | {exit_ts_str} | {t.get('side')} | {t.get('qty')} | {t.get('entry_price')} | {t.get('exit_price', 'N/A')} | {t.get('pnl', 0)} |")
