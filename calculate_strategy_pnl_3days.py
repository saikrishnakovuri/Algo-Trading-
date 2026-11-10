import json
from collections import defaultdict

trade_file = 'data/live_paper_trades.json'

with open(trade_file, 'r') as f:
    trades = json.load(f)

# Dates to consider
dates_to_show = ["2026-05-20", "2026-05-19", "2026-05-18"]

# Filter out only CLOSED trades within the specified dates
closed_trades = [
    t for t in trades 
    if t.get('status') == 'CLOSED' and any(t.get('opened_at', '').startswith(d) for d in dates_to_show)
]

# We should group by strategy and calculate P&L, trade counts
strategy_stats = defaultdict(lambda: {'pnl': 0.0, 'count': 0, 'wins': 0, 'losses': 0})

for t in closed_trades:
    strat = t.get('strategy', 'UNKNOWN')
    pnl = t.get('pnl', 0.0)
    
    strategy_stats[strat]['pnl'] += pnl
    strategy_stats[strat]['count'] += 1
    if pnl > 0:
        strategy_stats[strat]['wins'] += 1
    elif pnl < 0:
        strategy_stats[strat]['losses'] += 1

print("\n### Strategy-wise Performance (Last 3 Days: 18th to 20th May 2026)")
print(f"| Strategy | Total Trades | Wins | Losses | Net P&L (₹) |")
print(f"| :--- | :---: | :---: | :---: | :--- |")

# Sort strategies by P&L descending
sorted_strats = sorted(strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)

total_pnl = 0.0
total_trades = 0

for strat, stats in sorted_strats:
    print(f"| {strat} | {stats['count']} | {stats['wins']} | {stats['losses']} | {stats['pnl']:.2f} |")
    total_pnl += stats['pnl']
    total_trades += stats['count']

print(f"| **TOTAL** | **{total_trades}** | **-** | **-** | **{total_pnl:.2f}** |")

