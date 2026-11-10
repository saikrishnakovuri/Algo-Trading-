import pandas as pd
from datetime import time

WINNING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"

# Load data
winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')

# Parse entry times
winning_df['entry_time'] = pd.to_datetime(winning_df['Entry_Time'], errors='coerce').dt.time
losing_df['entry_time'] = pd.to_datetime(losing_df['Entry_Time'], errors='coerce').dt.time

# Filter for trades from 9:45 onwards (remove 9:00-9:44:59)
cutoff_time = time(9, 45, 0)

winning_filtered = winning_df[winning_df['entry_time'] >= cutoff_time]
losing_filtered = losing_df[losing_df['entry_time'] >= cutoff_time]

# Calculate metrics
total_wins = len(winning_filtered)
total_losses = len(losing_filtered)
total_trades = total_wins + total_losses

win_pnl = winning_filtered['PnL'].sum()
loss_pnl = losing_filtered['PnL'].sum()
net_pnl = win_pnl + loss_pnl

win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
avg_win = winning_filtered['PnL'].mean() if total_wins > 0 else 0
avg_loss = losing_filtered['PnL'].mean() if total_losses > 0 else 0

print("=" * 70)
print("ANALYSIS: REMOVING TRADES BEFORE 9:45 AM")
print("=" * 70)
print()
print("ORIGINAL METRICS (All Trades):")
print(f"  Total Trades: 623")
print(f"  Winning Trades: 299")
print(f"  Losing Trades: 324")
print(f"  Win Rate: 47.99%")
print(f"  Net P&L: ₹349,688.06")
print()
print("-" * 70)
print()
print("NEW METRICS (From 9:45 AM onwards):")
print(f"  Total Trades: {total_trades}")
print(f"  Winning Trades: {total_wins}")
print(f"  Losing Trades: {total_losses}")
print(f"  Win Rate: {win_rate:.2f}%")
print(f"  Total Profit (Wins): ₹{win_pnl:,.2f}")
print(f"  Total Loss (Losses): ₹{loss_pnl:,.2f}")
print(f"  Net P&L: ₹{net_pnl:,.2f}")
print(f"  Average Win: ₹{avg_win:,.2f}")
print(f"  Average Loss: ₹{avg_loss:,.2f}")
print()
print("-" * 70)
print()
print("TRADES REMOVED (9:00 - 9:44:59):")
removed_wins = 299 - total_wins
removed_losses = 324 - total_losses
removed_total = removed_wins + removed_losses
removed_win_rate = (removed_wins / removed_total * 100) if removed_total > 0 else 0
removed_pnl = (winning_df[winning_df['entry_time'] < cutoff_time]['PnL'].sum() + 
               losing_df[losing_df['entry_time'] < cutoff_time]['PnL'].sum())
print(f"  Total Removed: {removed_total}")
print(f"  Wins Removed: {removed_wins}")
print(f"  Losses Removed: {removed_losses}")
print(f"  Removed Win Rate: {removed_win_rate:.2f}%")
print(f"  Removed P&L: ₹{removed_pnl:,.2f}")
print()
print("=" * 70)
print("IMPROVEMENT ANALYSIS:")
improvement = win_rate - 47.99
pnl_diff = net_pnl - 349688.06
print(f"  Win Rate Change: {improvement:+.2f}% (from 47.99% to {win_rate:.2f}%)")
print(f"  P&L Change: ₹{pnl_diff:+,.2f} (from ₹349,688.06 to ₹{net_pnl:,.2f})")
print(f"  {'IMPROVEMENT!' if pnl_diff > 0 else 'DEGRADATION!'}")
print("=" * 70)
