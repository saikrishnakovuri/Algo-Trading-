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

print(f"Found {len(nifty_trades)} NIFTY trades in live_paper_trades.json:\n")
for t in sorted(nifty_trades.values(), key=lambda x: x.get('opened_at', '')):
    print(f"Trade ID  : {t.get('trade_id')}")
    print(f"Entry Time: {t.get('opened_at')}")
    print(f"Exit Time : {t.get('closed_at', 'OPEN')}")
    print(f"Side      : {t.get('side')} | Qty: {t.get('qty')}")
    print(f"Entry Px  : {t.get('entry_price')}")
    print(f"Exit Px   : {t.get('exit_price', 'N/A')}")
    print(f"P&L       : {t.get('pnl', 0)}")
    print('-'*40)
