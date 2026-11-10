import json
from datetime import datetime
from collections import Counter

trade_file = 'data/live_paper_trades.json'

with open(trade_file, 'r') as f:
    trades = json.load(f)

today = "2026-05-20"
today_trades = [t for t in trades if t['opened_at'].startswith(today)]

closed_ids = {t['trade_id'] for t in trades if t['status'] == 'CLOSED'}
active_trades = [t for t in today_trades if t['status'] == 'OPEN' and t['trade_id'] not in closed_ids]

closed_now = []
if active_trades:
    print(f"Found {len(active_trades)} open trades. Force closing them...")
    now_str = datetime.now().isoformat()
    for t in active_trades:
        # Create a closed entry for the open trade
        closed_trade = t.copy()
        closed_trade['status'] = 'CLOSED'
        closed_trade['exit_reason'] = 'FORCE_CLOSE_EOD'
        closed_trade['closed_at'] = now_str
        # If no exit price, use entry price for zero PnL, or we could just use 0 PnL
        closed_trade['exit_price'] = t['entry_price'] 
        closed_trade['pnl'] = 0.0
        trades.append(closed_trade)
        closed_now.append(t['symbol'])
    
    with open(trade_file, 'w') as f:
        json.dump(trades, f, indent=2)
else:
    print("All trades for today are already closed.")

# Recalculate summary
today_trades = [t for t in trades if t['opened_at'].startswith(today)]
closed_trades = [t for t in today_trades if t['status'] == 'CLOSED']

total_pnl = sum(t['pnl'] for t in closed_trades)
winning_trades = [t for t in closed_trades if t['pnl'] > 0]
losing_trades = [t for t in closed_trades if t['pnl'] < 0]

# Strategy breakdown
unique_trades = {}
for t in today_trades:
    tid = t['trade_id']
    if tid not in unique_trades:
        unique_trades[tid] = t

strategies = [t['strategy'] for t in unique_trades.values()]
strategy_counts = Counter(strategies)

print("\n--- TODAY'S SUMMARY (2026-05-20) ---")
if closed_now:
    print(f"Force Closed Just Now: {', '.join(closed_now)}")

print(f"Total Trades Taken: {len(unique_trades)}")
print(f"Total Closed Legs (including partials/updates): {len(closed_trades)}")
print(f"Net P&L: ₹ {total_pnl:.2f}")
print(f"Winning Trades: {len(winning_trades)}")
print(f"Losing Trades: {len(losing_trades)}")
print(f"Break-Even/Force Closed: {len(closed_trades) - len(winning_trades) - len(losing_trades)}")

print("\n--- STRATEGY PERFORMANCE ---")
for strategy, count in strategy_counts.items():
    strat_pnl = sum(t['pnl'] for t in closed_trades if t['strategy'] == strategy)
    print(f"  - {strategy}: {count} trades | P&L: ₹ {strat_pnl:.2f}")

