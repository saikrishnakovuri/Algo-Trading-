#!/usr/bin/env python3
"""
Extract key audit metrics to a concise summary file
"""

import pandas as pd

WINNING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"
OUTPUT_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\TRADE_AUDIT_SUMMARY.txt"

winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')

with open(OUTPUT_FILE, 'w') as f:
    f.write("=" * 100 + "\n")
    f.write("COMPREHENSIVE TRADE AUDIT - MAY 9, 2026\n")
    f.write("=" * 100 + "\n\n")
    
    # Basic counts
    f.write("1. TRADE SUMMARY\n")
    f.write("-" * 100 + "\n")
    f.write(f"Winning Trades: {len(winning_df)}\n")
    f.write(f"Losing Trades: {len(losing_df)}\n")
    f.write(f"Total Trades: {len(winning_df) + len(losing_df)}\n")
    f.write(f"Win Rate: {len(winning_df)/(len(winning_df)+len(losing_df))*100:.2f}%\n")
    f.write(f"Loss Rate: {len(losing_df)/(len(winning_df)+len(losing_df))*100:.2f}%\n\n")
    
    # P&L Analysis
    f.write("2. PROFIT/LOSS ANALYSIS\n")
    f.write("-" * 100 + "\n")
    
    pnl_col = 'PnL'
    win_total = winning_df[pnl_col].sum()
    loss_total = losing_df[pnl_col].sum()
    net_total = win_total + loss_total
    
    f.write(f"Total Winning P&L: INR {win_total:,.2f}\n")
    f.write(f"Total Losing P&L: INR {loss_total:,.2f}\n")
    f.write(f"NET P&L: INR {net_total:,.2f}\n\n")
    
    f.write(f"Average Win: INR {winning_df[pnl_col].mean():,.2f}\n")
    f.write(f"Average Loss: INR {losing_df[pnl_col].mean():,.2f}\n")
    f.write(f"Largest Win: INR {winning_df[pnl_col].max():,.2f}\n")
    f.write(f"Largest Loss: INR {losing_df[pnl_col].min():,.2f}\n\n")
    
    avg_win = winning_df[pnl_col].mean()
    avg_loss = abs(losing_df[pnl_col].mean())
    f.write(f"Reward Ratio (Win/Loss): {avg_win/avg_loss:.2f}\n")
    f.write(f"Profit Factor: {win_total/abs(loss_total):.2f}x\n\n")
    
    # Strategy breakdown
    f.write("3. STRATEGY ANALYSIS\n")
    f.write("-" * 100 + "\n")
    
    strategy_col = winning_df.columns[winning_df.columns.str.contains('Strategy', case=False)][0] if any(winning_df.columns.str.contains('Strategy', case=False)) else None
    if strategy_col:
        f.write(f"Winning by {strategy_col}:\n")
        f.write(str(winning_df[strategy_col].value_counts()) + "\n\n")
        f.write(f"Losing by {strategy_col}:\n")
        f.write(str(losing_df[strategy_col].value_counts()) + "\n\n")
    
    # Direction analysis
    f.write("4. DIRECTION/INSTRUMENT ANALYSIS\n")
    f.write("-" * 100 + "\n")
    
    direction_col = 'Direction'
    f.write(f"Winning by Direction:\n")
    f.write(str(winning_df[direction_col].value_counts()) + "\n\n")
    f.write(f"Losing by Direction:\n")
    f.write(str(losing_df[direction_col].value_counts()) + "\n\n")
    
    symbol_col = 'Symbol'
    f.write(f"Winning by Symbol:\n")
    f.write(str(winning_df[symbol_col].value_counts()) + "\n\n")
    f.write(f"Losing by Symbol:\n")
    f.write(str(losing_df[symbol_col].value_counts()) + "\n\n")
    
    # Entry timing
    f.write("5. ENTRY TIMING ANALYSIS\n")
    f.write("-" * 100 + "\n")
    
    winning_df['entry_hour'] = pd.to_datetime(winning_df['Entry_Time'], errors='coerce').dt.hour
    losing_df['entry_hour'] = pd.to_datetime(losing_df['Entry_Time'], errors='coerce').dt.hour
    
    f.write("Winning entries by hour:\n")
    f.write(str(winning_df['entry_hour'].value_counts().sort_index()) + "\n\n")
    f.write("Losing entries by hour:\n")
    f.write(str(losing_df['entry_hour'].value_counts().sort_index()) + "\n\n")
    
    # Reason analysis
    f.write("6. REASON/OUTCOME ANALYSIS\n")
    f.write("-" * 100 + "\n")
    
    reason_col = 'Reason' if 'Reason' in winning_df.columns else None
    result_col = 'Result' if 'Result' in winning_df.columns else None
    
    if reason_col:
        f.write(f"Winning by Reason:\n")
        f.write(str(winning_df[reason_col].value_counts()) + "\n\n")
        f.write(f"Losing by Reason:\n")
        f.write(str(losing_df[reason_col].value_counts()) + "\n\n")
    
    if result_col:
        f.write(f"Winning by Result:\n")
        f.write(str(winning_df[result_col].value_counts()) + "\n\n")
        f.write(f"Losing by Result:\n")
        f.write(str(losing_df[result_col].value_counts()) + "\n\n")
    
    # Top and bottom trades
    f.write("7. TOP 10 WINNING TRADES (WHAT WENT WELL)\n")
    f.write("-" * 100 + "\n")
    top_wins = winning_df.nlargest(10, pnl_col)[['Symbol', 'Entry_Time', 'Exit_Time', 'Direction', 'Entry_Price', 'Exit_Price', 'PnL', 'Profit_Pct']]
    f.write(top_wins.to_string() + "\n\n")
    
    f.write("8. TOP 10 LOSING TRADES (WHAT WENT WRONG)\n")
    f.write("-" * 100 + "\n")
    top_losses = losing_df.nsmallest(10, pnl_col)[['Symbol', 'Entry_Time', 'Exit_Time', 'Direction', 'Entry_Price', 'Exit_Price', 'PnL', 'Profit_Pct']]
    f.write(top_losses.to_string() + "\n\n")
    
    # All winning trades
    f.write("9. ALL WINNING TRADES (COMPLETE LIST)\n")
    f.write("-" * 100 + "\n")
    f.write(winning_df.to_string() + "\n\n")
    
    # All losing trades
    f.write("10. ALL LOSING TRADES (COMPLETE LIST)\n")
    f.write("-" * 100 + "\n")
    f.write(losing_df.to_string() + "\n")

print(f"Audit summary written to: {OUTPUT_FILE}")
