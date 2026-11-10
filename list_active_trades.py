import json
from datetime import datetime

with open('data/live_paper_trades.json', 'r') as f:
    trades = json.load(f)

# Identify truly open trades (status=OPEN and not closed later)
closed_ids = {t['trade_id'] for t in trades if t['status'] == 'CLOSED'}
active_trades = [t for t in trades if t['status'] == 'OPEN' and t['trade_id'] not in closed_ids]

print(f"{'Symbol':<12} | {'Side':<4} | {'Entry':<8} | {'SL':<8} | {'TP':<8} | {'Opened At'}")
print("-" * 65)
for t in active_trades:
    print(f"{t['symbol']:<12} | {t['side']:<4} | {t['entry_price']:<8.2f} | {t['sl']:<8.2f} | {t['tp']:<8.2f} | {t['opened_at']}")
