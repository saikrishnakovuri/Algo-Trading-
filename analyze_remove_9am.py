import pandas as pd

WINNING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"

# Load data
winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')

# Parse entry hour
winning_df['entry_hour'] = pd.to_datetime(winning_df['Entry_Time'], errors='coerce').dt.hour
losing_df['entry_hour'] = pd.to_datetime(losing_df['Entry_Time'], errors='coerce').dt.hour

# SCENARIO 1: Remove 9:00 hour completely (9:00-9:59)
print("=" * 70)
print("SCENARIO 1: REMOVING 9:00 AM HOUR (9:00-9:59)")
print("=" * 70)
print()

winning_filtered = winning_df[winning_df['entry_hour'] != 9]
losing_filtered = losing_df[losing_df['entry_hour'] != 9]

total_wins = len(winning_filtered)
total_losses = len(losing_filtered)
total_trades = total_wins + total_losses

win_pnl = winning_filtered['PnL'].sum()
loss_pnl = losing_filtered['PnL'].sum()
net_pnl = win_pnl + loss_pnl

win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
avg_win = winning_filtered['PnL'].mean() if total_wins > 0 else 0
avg_loss = losing_filtered['PnL'].mean() if total_losses > 0 else 0
profit_factor = win_pnl / abs(loss_pnl) if loss_pnl != 0 else 0
reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

print("ORIGINAL METRICS (All Trades 9:00-12:59):")
print(f"  Total Trades: 623")
print(f"  Winning Trades: 299 (47.99%)")
print(f"  Losing Trades: 324 (52.01%)")
print(f"  Net P&L: ₹349,688.06")
print(f"  Avg Win: ₹4,512.03 | Avg Loss: ₹-3,084.59")
print()
print("-" * 70)
print()
print("NEW METRICS (Only 10:00-12:59, removing 9:00 hour):")
print(f"  Total Trades: {total_trades}")
print(f"  Winning Trades: {total_wins} ({win_rate:.2f}%)")
print(f"  Losing Trades: {total_losses} ({100-win_rate:.2f}%)")
print(f"  Net P&L: ₹{net_pnl:,.2f}")
print(f"  Avg Win: ₹{avg_win:,.2f} | Avg Loss: ₹{avg_loss:,.2f}")
print(f"  Profit Factor: {profit_factor:.2f}x")
print(f"  Reward Ratio: {reward_ratio:.2f}:1")
print()
print("-" * 70)
print()
print("TRADES REMOVED (9:00-9:59):")
removed_wins = 33
removed_losses = 50
removed_total = 83
removed_win_rate = (removed_wins / removed_total * 100)
removed_pnl = (winning_df[winning_df['entry_hour'] == 9]['PnL'].sum() + 
               losing_df[losing_df['entry_hour'] == 9]['PnL'].sum())
print(f"  Total Removed: {removed_total} trades")
print(f"  Wins Removed: {removed_wins} ({removed_win_rate:.2f}%)")
print(f"  Losses Removed: {removed_losses} ({100-removed_win_rate:.2f}%)")
print(f"  Removed P&L: ₹{removed_pnl:,.2f}")
print()
print("=" * 70)
print("IMPROVEMENT ANALYSIS:")
improvement = win_rate - 47.99
pnl_diff = net_pnl - 349688.06
print(f"  Win Rate Change: {improvement:+.2f}% (from 47.99% to {win_rate:.2f}%)")
print(f"  P&L Change: ₹{pnl_diff:+,.2f}")
print(f"  Status: {'BETTER!' if pnl_diff > 0 else 'WORSE!' if pnl_diff < 0 else 'SAME'}")
print("=" * 70)

print()
print()
print("=" * 70)
print("BREAKDOWN BY HOUR (Remaining Trades):")
print("=" * 70)
print()
print("WINNING TRADES by hour (9:00 removed):")
print(winning_filtered['entry_hour'].value_counts().sort_index())
print()
print("LOSING TRADES by hour (9:00 removed):")
print(losing_filtered['entry_hour'].value_counts().sort_index())
