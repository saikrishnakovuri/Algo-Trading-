#!/usr/bin/env python3
"""
Comprehensive Trade Analysis Script - Direct Execution
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
print("🤖 COMPREHENSIVE TRADE AUDIT REPORT")
print("=" * 100)

try:
    # Load Excel files with openpyxl engine explicitly
    winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
    losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')
    
    print(f"\n✅ Successfully loaded data:")
    print(f"   Winning trades: {len(winning_df)} rows")
    print(f"   Losing trades: {len(losing_df)} rows")
    print(f"   Total trades: {len(winning_df) + len(losing_df)} rows")
    
except Exception as e:
    print(f"❌ Error loading files: {e}")
    sys.exit(1)

# ============================================================================
# 1. COLUMN OVERVIEW
# ============================================================================
print(f"\n{'=' * 100}")
print("📋 COLUMN STRUCTURE")
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
print("📊 TRADE SUMMARY STATISTICS")
print("=" * 100)

win_count = len(winning_df)
loss_count = len(losing_df)
total_trades = win_count + loss_count
win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

print(f"\n📈 Trade Count:")
print(f"  Winning Trades: {win_count:,}")
print(f"  Losing Trades: {loss_count:,}")
print(f"  Total Trades: {total_trades:,}")
print(f"  Win Rate: {win_rate:.2f}%")

# ============================================================================
# 3. PROFIT/LOSS ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("💰 PROFIT/LOSS ANALYSIS")
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
    
    print(f"\n💵 {pnl_col}:")
    print(f"  Winning Trades Total: ₹{win_total_pnl:,.2f}")
    print(f"  Losing Trades Total: ₹{loss_total_pnl:,.2f}")
    print(f"  Net P&L: ₹{total_pnl:,.2f}")
    print(f"  Avg Win: ₹{winning_df[pnl_col].mean():,.2f}")
    print(f"  Avg Loss: ₹{losing_df[pnl_col].mean():,.2f}")
    print(f"  Max Win: ₹{winning_df[pnl_col].max():,.2f}")
    print(f"  Max Loss: ₹{losing_df[pnl_col].min():,.2f}")
    
    # Profit factor
    if abs(loss_total_pnl) > 0:
        profit_factor = win_total_pnl / abs(loss_total_pnl)
        print(f"  Profit Factor: {profit_factor:.2f}x")

if pct_cols:
    pct_col = pct_cols[0]
    print(f"\n📊 {pct_col}:")
    print(f"  Winning Trades Avg: {winning_df[pct_col].mean():.4f}%")
    print(f"  Losing Trades Avg: {losing_df[pct_col].mean():.4f}%")
    print(f"  Overall Avg Return: {(winning_df[pct_col].mean() * win_rate/100 + losing_df[pct_col].mean() * (100-win_rate)/100):.4f}%")

# ============================================================================
# 4. STRATEGY BREAKDOWN
# ============================================================================
print(f"\n{'=' * 100}")
print("🎯 STRATEGY BREAKDOWN")
print("=" * 100)

strategy_cols = [col for col in winning_df.columns if 'strategy' in col.lower() or 'signal' in col.lower()]
if strategy_cols:
    strategy_col = strategy_cols[0]
    print(f"\n{strategy_col} - Winning Trades:")
    print(winning_df[strategy_col].value_counts())
    print(f"\n{strategy_col} - Losing Trades:")
    print(losing_df[strategy_col].value_counts())

# ============================================================================
# 5. TIME ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("⏰ TEMPORAL ANALYSIS")
print("=" * 100)

entry_cols = [col for col in winning_df.columns if 'entry' in col.lower() and 'time' in col.lower()]
exit_cols = [col for col in winning_df.columns if 'exit' in col.lower() and 'time' in col.lower()]

if entry_cols:
    entry_col = entry_cols[0]
    print(f"\n📍 Entry Times Analysis:")
    
    # Extract hour from entry time
    try:
        winning_df['entry_hour'] = pd.to_datetime(winning_df[entry_col], errors='coerce').dt.hour
        losing_df['entry_hour'] = pd.to_datetime(losing_df[entry_col], errors='coerce').dt.hour
        
        print(f"\n  Winning Trades - Entry Hour Distribution:")
        print(winning_df['entry_hour'].value_counts().sort_index())
        
        print(f"\n  Losing Trades - Entry Hour Distribution:")
        print(losing_df['entry_hour'].value_counts().sort_index())
    except Exception as e:
        print(f"  ⚠️  Could not parse entry times: {e}")

# ============================================================================
# 6. DIRECTION/SIDE ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("📊 DIRECTION/SIDE ANALYSIS")
print("=" * 100)

direction_cols = [col for col in winning_df.columns if 'direction' in col.lower()]
if direction_cols:
    direction_col = direction_cols[0]
    print(f"\n{direction_col} Distribution:")
    print(f"\n  Winning Trades:")
    print(winning_df[direction_col].value_counts())
    print(f"\n  Losing Trades:")
    print(losing_df[direction_col].value_counts())

# ============================================================================
# 7. INSTRUMENT ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("📈 INSTRUMENT/SYMBOL ANALYSIS")
print("=" * 100)

symbol_cols = [col for col in winning_df.columns if 'symbol' in col.lower()]
if symbol_cols:
    symbol_col = symbol_cols[0]
    print(f"\n{symbol_col} Distribution:")
    print(f"\n  Winning Trades:")
    print(winning_df[symbol_col].value_counts())
    print(f"\n  Losing Trades:")
    print(losing_df[symbol_col].value_counts())

# ============================================================================
# 8. REASON/RESULT ANALYSIS
# ============================================================================
print(f"\n{'=' * 100}")
print("🔍 REASON/RESULT ANALYSIS - WHY TRADES WON/LOST")
print("=" * 100)

reason_cols = [col for col in winning_df.columns if 'reason' in col.lower() or 'result' in col.lower()]
for reason_col in reason_cols:
    if reason_col in winning_df.columns:
        print(f"\n{reason_col} - Winning Trades:")
        print(winning_df[reason_col].value_counts())
    if reason_col in losing_df.columns:
        print(f"\n{reason_col} - Losing Trades:")
        print(losing_df[reason_col].value_counts())

# ============================================================================
# 9. TOP TRADES
# ============================================================================
print(f"\n{'=' * 100}")
print("🏆 TOP 10 WINNING TRADES")
print("=" * 100)

if pnl_cols:
    pnl_col = pnl_cols[0]
    top_wins = winning_df.nlargest(10, pnl_col)[[col for col in winning_df.columns]]
    print("\n" + top_wins.to_string())

print(f"\n{'=' * 100}")
print("💔 TOP 10 LOSING TRADES")
print("=" * 100)

if pnl_cols:
    pnl_col = pnl_cols[0]
    top_losses = losing_df.nsmallest(10, pnl_col)[[col for col in losing_df.columns]]
    print("\n" + top_losses.to_string())

# ============================================================================
# 10. DETAILED TRADE LISTING
# ============================================================================
print(f"\n{'=' * 100}")
print("📋 ALL WINNING TRADES (Full List)")
print("=" * 100)
print("\n" + winning_df.to_string())

print(f"\n{'=' * 100}")
print("📋 ALL LOSING TRADES (Full List)")
print("=" * 100)
print("\n" + losing_df.to_string())

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print(f"\n{'=' * 100}")
print("✅ AUDIT COMPLETE")
print("=" * 100)
