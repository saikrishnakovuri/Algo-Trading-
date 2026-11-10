import json

with open('data/live_paper_trades.json', 'r') as f:
    data = json.load(f)

seen = {}
for t in data:
    if t.get('symbol') == 'NIFTY':
        tid = t['trade_id']
        if tid not in seen or abs(t.get('pnl', 0)) > abs(seen[tid].get('pnl', 0)):
            seen[tid] = t

today_trades = [t for t in seen.values() if t['opened_at'].startswith('2026-05-22')]

print(f'NIFTY trades opened on 2026-05-22: {len(today_trades)}')
for t in today_trades:
    print(f"{t['trade_id']} | {t['opened_at']} | PnL: {t.get('pnl')}")
