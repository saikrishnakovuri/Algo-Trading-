#!/usr/bin/env python3
"""
Comprehensive Trade Analysis Script
Analyzes winning and losing trades from Excel files
"""

import pandas as pd
import os
from datetime import datetime
from collections import defaultdict

# File paths
WINNING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"

def load_data():
    """Load both Excel files"""
    print("=" * 80)
    print("🔄 LOADING TRADE DATA...")
    print("=" * 80)
    
    try:
        winning_df = pd.read_excel(WINNING_FILE)
        print(f"✅ Loaded {WINNING_FILE}")
        print(f"   Rows: {len(winning_df)}, Columns: {len(winning_df.columns)}")
    except Exception as e:
        print(f"❌ Error loading winning file: {e}")
        winning_df = None
    
    try:
        losing_df = pd.read_excel(LOSING_FILE)
        print(f"✅ Loaded {LOSING_FILE}")
        print(f"   Rows: {len(losing_df)}, Columns: {len(losing_df.columns)}")
    except Exception as e:
        print(f"❌ Error loading losing file: {e}")
        losing_df = None
    
    return winning_df, losing_df

def analyze_trades(df, trade_type="WINNING"):
    """Perform detailed analysis on trades"""
    if df is None or len(df) == 0:
        print(f"\n⚠️  No {trade_type} trades to analyze")
        return
    
    print(f"\n{'=' * 80}")
    print(f"📊 DETAILED {trade_type} TRADES ANALYSIS")
    print(f"{'=' * 80}")
    
    # Display columns
    print(f"\n📋 Column Names ({len(df.columns)} columns):")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")
    
    # Display data types
    print(f"\n📝 Data Types:")
    print(df.dtypes)
    
    # Display first few rows
    print(f"\n📈 First 5 Rows (Sample):")
    print(df.head().to_string())
    
    # Summary statistics
    print(f"\n📊 Summary Statistics:")
    print(df.describe().to_string())
    
    # Check for date/time columns
    print(f"\n⏰ Temporal Analysis:")
    for col in df.columns:
        if any(x in col.lower() for x in ['date', 'time', 'entry', 'exit']):
            print(f"   {col}: {df[col].dtype}")
            if len(df) > 0:
                print(f"      Sample values: {df[col].head(3).tolist()}")
    
    # Check for profit/loss columns
    print(f"\n💰 Profit/Loss Analysis:")
    for col in df.columns:
        if any(x in col.lower() for x in ['pnl', 'profit', 'loss', 'gain', 'return']):
            print(f"   {col}: {df[col].dtype}")
            if df[col].dtype in ['float64', 'int64']:
                print(f"      Sum: {df[col].sum():,.2f}")
                print(f"      Mean: {df[col].mean():,.2f}")
                print(f"      Max: {df[col].max():,.2f}")
                print(f"      Min: {df[col].min():,.2f}")
    
    # Check for strategy columns
    print(f"\n🎯 Strategy Analysis:")
    for col in df.columns:
        if any(x in col.lower() for x in ['strategy', 'signal', 'type']):
            if df[col].dtype == 'object':
                print(f"   {col}:")
                print(f"      {df[col].value_counts().to_string()}")
    
    # Full data display
    print(f"\n🔍 Full Data Preview:")
    print(df.to_string())

def combined_analysis(winning_df, losing_df):
    """Analyze both winning and losing trades together"""
    print(f"\n{'=' * 80}")
    print(f"🔄 COMBINED ANALYSIS (WINNING + LOSING)")
    print(f"{'=' * 80}")
    
    if winning_df is None and losing_df is None:
        print("⚠️  No data to analyze")
        return
    
    win_count = len(winning_df) if winning_df is not None else 0
    loss_count = len(losing_df) if losing_df is not None else 0
    total_trades = win_count + loss_count
    
    print(f"\n📊 Trade Count Summary:")
    print(f"   Winning Trades: {win_count}")
    print(f"   Losing Trades: {loss_count}")
    print(f"   Total Trades: {total_trades}")
    
    if total_trades > 0:
        win_rate = (win_count / total_trades) * 100
        print(f"   Win Rate: {win_rate:.2f}%")
    
    # PnL analysis
    print(f"\n💰 Profit/Loss Summary:")
    
    if winning_df is not None:
        for col in winning_df.columns:
            if any(x in col.lower() for x in ['pnl', 'profit', 'gain', 'return']):
                if winning_df[col].dtype in ['float64', 'int64']:
                    total_profit = winning_df[col].sum()
                    avg_profit = winning_df[col].mean()
                    print(f"   {col} (WINNING):")
                    print(f"      Total: ₹{total_profit:,.2f}")
                    print(f"      Average: ₹{avg_profit:,.2f}")
    
    if losing_df is not None:
        for col in losing_df.columns:
            if any(x in col.lower() for x in ['pnl', 'loss', 'return']):
                if losing_df[col].dtype in ['float64', 'int64']:
                    total_loss = losing_df[col].sum()
                    avg_loss = losing_df[col].mean()
                    print(f"   {col} (LOSING):")
                    print(f"      Total: ₹{total_loss:,.2f}")
                    print(f"      Average: ₹{avg_loss:,.2f}")

def main():
    """Main analysis function"""
    print("\n")
    print("🤖 COMPREHENSIVE TRADE ANALYSIS SCRIPT")
    print("=" * 80)
    
    # Load data
    winning_df, losing_df = load_data()
    
    # Analyze individual files
    analyze_trades(winning_df, "WINNING")
    analyze_trades(losing_df, "LOSING")
    
    # Combined analysis
    combined_analysis(winning_df, losing_df)
    
    print(f"\n{'=' * 80}")
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
