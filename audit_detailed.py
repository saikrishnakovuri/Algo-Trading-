#!/usr/bin/env python3
"""
Comprehensive Trade Analysis Script - Direct Execution
Fixed for Windows encoding
"""

import pandas as pd
import os
import sys

# Set working directory
os.chdir(r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options")

# File paths (absolute)
WINNING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"

print("\n" + "=" * 100)
print("COMPREHENSIVE TRADE AUDIT REPORT - MAY 9, 2026")
print("=" * 100)

try:
    # Load Excel files with openpyxl engine explicitly
    winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
    losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')
    
    print(f"\nSUCCESS: Data loaded")
    print(f"  Winning trades: {len(winning_df)} rows")
    print(f"  Losing trades: {len(losing_df)} rows")
    print(f"  Total trades: {len(winning_df) + len(losing_df)} rows")
    
except Exception as e:
    print(f"ERROR: Could not load files: {e}")
    sys.exit(1)

# ============================================================================
# 1. COLUMN OVERVIEW
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 1: COLUMN STRUCTURE")
print("=" * 100)
print(f"\nWinning Trades Columns ({len(winning_df.columns)}):")
for i, col in enumerate(winning_df.columns, 1):
    print(f"  {i:2}. {col}")

print(f"\nData Types:")
for col, dtype in winning_df.dtypes.items():
    print(f"  {col}: {dtype}")

# ============================================================================
# 2. TRADE SUMMARY STATISTICS
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 2: TRADE SUMMARY STATISTICS")
print("=" * 100)

win_count = len(winning_df)
loss_count = len(losing_df)
total_trades = win_count + loss_count
win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

print(f"\nTrade Count Summary:")
print(f"  Winning Trades: {win_count:,}")
print(f"  Losing Trades: {loss_count:,}")
print(f"  Total Trades: {total_trades:,}")
print(f"  Win Rate: {win_rate:.2f}%")
print(f"  Loss Rate: {100-win_rate:.2f}%")

# ============================================================================
# 3. PROFIT/LOSS ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 3: PROFIT/LOSS ANALYSIS")
print("=" * 100)

# Find PnL column
pnl_cols = [col for col in winning_df.columns if 'pnl' in col.lower()]
profit_cols = [col for col in winning_df.columns if 'profit' in col.lower()]
pct_cols = [col for col in winning_df.columns if 'pct' in col.lower()]

if pnl_cols:
    pnl_col = pnl_cols[0]
    win_total_pnl = winning_df[pnl_col].sum()
    loss_total_pnl = losing_df[pnl_col].sum()
    total_pnl = win_total_pnl + loss_total_pnl
    
    print(f"\nProfit/Loss ({pnl_col}):")
    print(f"  Winning Trades Total: INR {win_total_pnl:,.2f}")
    print(f"  Losing Trades Total: INR {loss_total_pnl:,.2f}")
    print(f"  Net P&L: INR {total_pnl:,.2f}")
    print(f"\nAverages:")
    print(f"  Average Win: INR {winning_df[pnl_col].mean():,.2f}")
    print(f"  Average Loss: INR {losing_df[pnl_col].mean():,.2f}")
    print(f"\nExtremes:")
    print(f"  Max Win: INR {winning_df[pnl_col].max():,.2f}")
    print(f"  Max Loss: INR {losing_df[pnl_col].min():,.2f}")
    print(f"  Min Win: INR {winning_df[pnl_col].min():,.2f}")
    print(f"  Min Loss: INR {losing_df[pnl_col].max():,.2f}")
    
    # Risk reward analysis
    avg_win = winning_df[pnl_col].mean()
    avg_loss = abs(losing_df[pnl_col].mean())
    
    if avg_loss > 0:
        reward_ratio = avg_win / avg_loss
        print(f"\nRisk/Reward Analysis:")
        print(f"  Reward Ratio (Avg Win / Avg Loss): {reward_ratio:.2f}")
    
    # Profit factor
    if abs(loss_total_pnl) > 0:
        profit_factor = win_total_pnl / abs(loss_total_pnl)
        print(f"  Profit Factor (Total Wins / Total Losses): {profit_factor:.2f}x")

if pct_cols:
    pct_col = pct_cols[0]
    print(f"\nPercentage Returns ({pct_col}):")
    print(f"  Winning Trades Avg: {winning_df[pct_col].mean():.4f}%")
    print(f"  Losing Trades Avg: {losing_df[pct_col].mean():.4f}%")
    print(f"  Max Return: {winning_df[pct_col].max():.4f}%")
    print(f"  Max Loss %: {losing_df[pct_col].min():.4f}%")

# ============================================================================
# 4. STRATEGY BREAKDOWN
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 4: STRATEGY BREAKDOWN")
print("=" * 100)

strategy_cols = [col for col in winning_df.columns if 'strategy' in col.lower() or 'signal' in col.lower()]
if strategy_cols:
    strategy_col = strategy_cols[0]
    print(f"\nWinning Trades by {strategy_col}:")
    print(winning_df[strategy_col].value_counts())
    
    print(f"\nLosing Trades by {strategy_col}:")
    print(losing_df[strategy_col].value_counts())
    
    # Calculate win rate by strategy
    print(f"\nWin Rate by Strategy:")
    all_trades = pd.concat([
        winning_df[[strategy_col]].assign(result='WIN'),
        losing_df[[strategy_col]].assign(result='LOSS')
    ])
    
    for strategy in all_trades[strategy_col].unique():
        strategy_trades = all_trades[all_trades[strategy_col] == strategy]
        strategy_wins = len(strategy_trades[strategy_trades['result'] == 'WIN'])
        strategy_total = len(strategy_trades)
        strategy_wr = (strategy_wins / strategy_total * 100) if strategy_total > 0 else 0
        print(f"  {strategy}: {strategy_wins}/{strategy_total} wins ({strategy_wr:.2f}%)")

# ============================================================================
# 5. TIME ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 5: TEMPORAL ANALYSIS - TIMING OF TRADES")
print("=" * 100)

entry_cols = [col for col in winning_df.columns if 'entry' in col.lower() and 'time' in col.lower()]
exit_cols = [col for col in winning_df.columns if 'exit' in col.lower() and 'time' in col.lower()]

if entry_cols:
    entry_col = entry_cols[0]
    print(f"\nEntry Times Analysis ({entry_col}):")
    
    try:
        winning_df['entry_hour'] = pd.to_datetime(winning_df[entry_col], errors='coerce').dt.hour
        losing_df['entry_hour'] = pd.to_datetime(losing_df[entry_col], errors='coerce').dt.hour
        
        print(f"\n  Winning Trades - Entry Hour Distribution:")
        entry_hr_wins = winning_df['entry_hour'].value_counts().sort_index()
        for hr, count in entry_hr_wins.items():
            if pd.notna(hr):
                print(f"    Hour {int(hr):02d}:00 - {int(hr):02d}:59: {count} trades")
        
        print(f"\n  Losing Trades - Entry Hour Distribution:")
        entry_hr_loss = losing_df['entry_hour'].value_counts().sort_index()
        for hr, count in entry_hr_loss.items():
            if pd.notna(hr):
                print(f"    Hour {int(hr):02d}:00 - {int(hr):02d}:59: {count} trades")
                
        # Best hour analysis
        combined_hour_stats = pd.DataFrame({
            'Wins': entry_hr_wins,
            'Losses': entry_hr_loss
        }).fillna(0)
        combined_hour_stats['Win_Rate'] = combined_hour_stats['Wins'] / (combined_hour_stats['Wins'] + combined_hour_stats['Losses']) * 100
        
        print(f"\n  Win Rate by Entry Hour:")
        for hr in combined_hour_stats.index:
            if pd.notna(hr):
                wr = combined_hour_stats.loc[hr, 'Win_Rate']
                total = int(combined_hour_stats.loc[hr, 'Wins'] + combined_hour_stats.loc[hr, 'Losses'])
                print(f"    Hour {int(hr):02d}:00 - {int(hr):02d}:59: {wr:.2f}% ({total} trades)")
                
    except Exception as e:
        print(f"  Could not parse entry times: {e}")

# ============================================================================
# 6. DIRECTION/SIDE ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 6: DIRECTION/SIDE ANALYSIS - BULLISH vs BEARISH")
print("=" * 100)

direction_cols = [col for col in winning_df.columns if 'direction' in col.lower()]
if direction_cols:
    direction_col = direction_cols[0]
    print(f"\n{direction_col} Distribution:")
    print(f"\n  Winning Trades:")
    win_dirs = winning_df[direction_col].value_counts()
    for direction, count in win_dirs.items():
        print(f"    {direction}: {count}")
    
    print(f"\n  Losing Trades:")
    loss_dirs = losing_df[direction_col].value_counts()
    for direction, count in loss_dirs.items():
        print(f"    {direction}: {count}")
    
    # Win rate by direction
    print(f"\n  Win Rate by Direction:")
    all_dir_trades = pd.concat([
        winning_df[[direction_col]].assign(result='WIN'),
        losing_df[[direction_col]].assign(result='LOSS')
    ])
    
    for direction in all_dir_trades[direction_col].unique():
        dir_trades = all_dir_trades[all_dir_trades[direction_col] == direction]
        dir_wins = len(dir_trades[dir_trades['result'] == 'WIN'])
        dir_total = len(dir_trades)
        dir_wr = (dir_wins / dir_total * 100) if dir_total > 0 else 0
        print(f"    {direction}: {dir_wins}/{dir_total} ({dir_wr:.2f}%)")

# ============================================================================
# 7. INSTRUMENT ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 7: INSTRUMENT ANALYSIS - SYMBOLS TRADED")
print("=" * 100)

symbol_cols = [col for col in winning_df.columns if 'symbol' in col.lower()]
if symbol_cols:
    symbol_col = symbol_cols[0]
    print(f"\n{symbol_col} Distribution:")
    print(f"\n  Winning Trades:")
    print(winning_df[symbol_col].value_counts())
    
    print(f"\n  Losing Trades:")
    print(losing_df[symbol_col].value_counts())
    
    # Win rate by instrument
    print(f"\n  Win Rate by Instrument:")
    all_sym_trades = pd.concat([
        winning_df[[symbol_col]].assign(result='WIN'),
        losing_df[[symbol_col]].assign(result='LOSS')
    ])
    
    for symbol in all_sym_trades[symbol_col].unique():
        sym_trades = all_sym_trades[all_sym_trades[symbol_col] == symbol]
        sym_wins = len(sym_trades[sym_trades['result'] == 'WIN'])
        sym_total = len(sym_trades)
        sym_wr = (sym_wins / sym_total * 100) if sym_total > 0 else 0
        print(f"    {symbol}: {sym_wins}/{sym_total} ({sym_wr:.2f}%)")

# ============================================================================
# 8. REASON/RESULT ANALYSIS - WHY DID TRADES WIN OR LOSE
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 8: REASON/RESULT ANALYSIS - WHY TRADES WON/LOST")
print("=" * 100)

reason_cols = [col for col in winning_df.columns if 'reason' in col.lower() or 'result' in col.lower()]
for reason_col in reason_cols:
    if reason_col in winning_df.columns and reason_col != 'Result':
        print(f"\n{reason_col} - Winning Trades:")
        print(winning_df[reason_col].value_counts())
    if reason_col in losing_df.columns and reason_col != 'Result':
        print(f"\n{reason_col} - Losing Trades:")
        print(losing_df[reason_col].value_counts())

# Check for Result column specifically
if 'Result' in winning_df.columns:
    print(f"\nResult - Winning Trades:")
    print(winning_df['Result'].value_counts())
if 'Result' in losing_df.columns:
    print(f"\nResult - Losing Trades:")
    print(losing_df['Result'].value_counts())

if 'Reason' in winning_df.columns:
    print(f"\nReason - Winning Trades:")
    print(winning_df['Reason'].value_counts())
if 'Reason' in losing_df.columns:
    print(f"\nReason - Losing Trades:")
    print(losing_df['Reason'].value_counts())

# ============================================================================
# 9. TOP TRADES - WHAT WENT WELL
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 9: TOP 10 WINNING TRADES - WHAT WENT WELL")
print("=" * 100)

if pnl_cols:
    pnl_col = pnl_cols[0]
    top_wins = winning_df.nlargest(10, pnl_col)
    print(f"\nTop 10 Best Trades by {pnl_col}:\n")
    print(top_wins.to_string())

# ============================================================================
# 10. WORST TRADES - WHAT WENT WRONG
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 10: TOP 10 LOSING TRADES - WHAT WENT WRONG")
print("=" * 100)

if pnl_cols:
    pnl_col = pnl_cols[0]
    top_losses = losing_df.nsmallest(10, pnl_col)
    print(f"\nTop 10 Worst Trades by {pnl_col}:\n")
    print(top_losses.to_string())

# ============================================================================
# 11. DETAILED TRADE LISTING
# ============================================================================
print(f"\n{'=' * 100}")
print("SECTION 11: ALL WINNING TRADES - COMPLETE LIST")
print("=" * 100)
print("\n" + winning_df.to_string())

print(f"\n{'=' * 100}")
print("SECTION 12: ALL LOSING TRADES - COMPLETE LIST")
print("=" * 100)
print("\n" + losing_df.to_string())

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print(f"\n{'=' * 100}")
print("AUDIT COMPLETE - READY FOR NEXT QUESTIONS")
print("=" * 100)
print("\nAnalysis Summary:")
print(f"  Total Trades Analyzed: {total_trades}")
print(f"  Win Rate: {win_rate:.2f}%")
if 'PnL' in winning_df.columns:
    total_pnl = winning_df['PnL'].sum() + losing_df['PnL'].sum()
    print(f"  Net Profit/Loss: INR {total_pnl:,.2f}")
