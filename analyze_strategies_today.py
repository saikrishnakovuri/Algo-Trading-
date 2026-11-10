import json
from collections import Counter

with open('data/live_paper_trades.json', 'r') as f:
    trades = json.load(f)

today = "2026-05-20"
today_trades = [t for t in trades if t['opened_at'].startswith(today)]

# We only care about unique trade IDs to count trades accurately
unique_trades = {}
for t in today_trades:
    tid = t['trade_id']
    if tid not in unique_trades:
        unique_trades[tid] = t

strategies = [t['strategy'] for t in unique_trades.values()]
strategy_counts = Counter(strategies)

print("Strategies used today (2026-05-20):")
for strategy, count in strategy_counts.items():
    # Calculate P&L for this strategy
    strategy_pnl = sum(t['pnl'] for t in today_trades if t['strategy'] == strategy and t['status'] == 'CLOSED')
    print(f"  - {strategy}: {count} trades, P&L: {strategy_pnl:.2f}")
