"""
Backtest Results Analyzer
═════════════════════════
Reads combined_backtest_results.csv and generates detailed analysis.

Usage:
    python scripts/analyze_backtest.py
    python scripts/analyze_backtest.py --file data/backtest_results/combined_backtest_results.csv
"""

import pandas as pd
import sys
import os

def analyze(filepath="data/backtest_results/combined_backtest_results.csv"):
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"ERROR: Could not read file: {e}")
        return

    print(f"\n{'='*70}")
    print(f" MULTI-STRATEGY BACKTEST ANALYSIS")
    print(f" File: {filepath}")
    print(f" Total trades: {len(df)}")
    print(f"{'='*70}\n")

    # Overall summary
    total_trades = len(df)
    if total_trades == 0:
        print("NO TRADES FOUND.")
        return

    wins = df[df['R_Multiple'] > 0]
    losses = df[df['R_Multiple'] <= 0]
    win_rate = len(wins) / total_trades * 100
    avg_r = df['R_Multiple'].mean()
    total_pnl = df['P&L_INR'].sum() if 'P&L_INR' in df.columns else df['P&L_Points'].sum()

    gross_profit = wins['R_Multiple'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['R_Multiple'].sum()) if len(losses) > 0 else 0.001
    profit_factor = gross_profit / gross_loss

    print(f"  OVERALL RESULTS")
    print(f"  {'─'*40}")
    print(f"  Total Trades:    {total_trades}")
    print(f"  Win Rate:        {win_rate:.1f}%")
    print(f"  Avg R-Multiple:  {avg_r:+.3f}R")
    print(f"  Expectancy:      {avg_r:+.3f}R per trade")
    print(f"  Profit Factor:   {profit_factor:.2f}")
    print(f"  Total P&L:       {total_pnl:+,.0f}")
    print(f"  Best Trade:      {df['R_Multiple'].max():+.2f}R")
    print(f"  Worst Trade:     {df['R_Multiple'].min():+.2f}R")
    if 'Bars_Held' in df.columns:
        print(f"  Avg Bars Held:   {df['Bars_Held'].mean():.1f}")
    print()

    # Per-strategy breakdown
    if 'Strategy' in df.columns:
        print(f"  PER-STRATEGY BREAKDOWN")
        print(f"  {'─'*60}")
        print(f"  {'Strategy':<20} {'Trades':>7} {'Win%':>7} {'Avg R':>8} {'PF':>6} {'P&L':>10}")
        print(f"  {'─'*60}")

        for strat in sorted(df['Strategy'].unique()):
            sdf = df[df['Strategy'] == strat]
            s_wins = sdf[sdf['R_Multiple'] > 0]
            s_losses = sdf[sdf['R_Multiple'] <= 0]
            s_wr = len(s_wins) / len(sdf) * 100 if len(sdf) > 0 else 0
            s_avg_r = sdf['R_Multiple'].mean()
            s_gp = s_wins['R_Multiple'].sum() if len(s_wins) > 0 else 0
            s_gl = abs(s_losses['R_Multiple'].sum()) if len(s_losses) > 0 else 0.001
            s_pf = s_gp / s_gl
            s_pnl = sdf['P&L_INR'].sum() if 'P&L_INR' in sdf.columns else sdf['P&L_Points'].sum()
            print(f"  {strat:<20} {len(sdf):>7} {s_wr:>6.1f}% {s_avg_r:>+7.3f} {s_pf:>6.2f} {s_pnl:>+10,.0f}")

        print()

    # Per-stock top/bottom
    if 'Symbol' in df.columns:
        stock_pnl = df.groupby('Symbol')['R_Multiple'].agg(['sum', 'count', 'mean']).sort_values('sum', ascending=False)
        stock_pnl.columns = ['Total_R', 'Trades', 'Avg_R']

        print(f"  TOP 10 STOCKS (by Total R)")
        print(f"  {'─'*50}")
        for sym, row in stock_pnl.head(10).iterrows():
            print(f"  {sym:<15} {row['Total_R']:>+7.2f}R  ({int(row['Trades'])} trades, {row['Avg_R']:>+.2f}R avg)")

        print(f"\n  BOTTOM 10 STOCKS (by Total R)")
        print(f"  {'─'*50}")
        for sym, row in stock_pnl.tail(10).iterrows():
            print(f"  {sym:<15} {row['Total_R']:>+7.2f}R  ({int(row['Trades'])} trades, {row['Avg_R']:>+.2f}R avg)")
        print()

    # Exit type breakdown
    if 'Exit_Type' in df.columns:
        print(f"  EXIT TYPE BREAKDOWN")
        print(f"  {'─'*50}")
        for exit_type in df['Exit_Type'].unique():
            edf = df[df['Exit_Type'] == exit_type]
            e_wr = len(edf[edf['R_Multiple'] > 0]) / len(edf) * 100 if len(edf) > 0 else 0
            print(f"  {exit_type:<20} {len(edf):>5} trades  Win: {e_wr:.1f}%  Avg R: {edf['R_Multiple'].mean():+.3f}")
        print()

    # Time analysis
    if 'Date' in df.columns:
        # Try to parse dates for day-of-week analysis
        try:
            df['_date'] = pd.to_datetime(df['Date'])
            df['_dow'] = df['_date'].dt.day_name()
            print(f"  WIN RATE BY DAY OF WEEK")
            print(f"  {'─'*40}")
            for dow in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                ddf = df[df['_dow'] == dow]
                if len(ddf) > 0:
                    d_wr = len(ddf[ddf['R_Multiple'] > 0]) / len(ddf) * 100
                    print(f"  {dow:<12} {len(ddf):>4} trades  Win: {d_wr:.1f}%")
            print()
        except Exception:
            pass

    print(f"{'='*70}")
    print(f" VERDICT:")
    if avg_r > 0.1:
        print(f" POSITIVE EDGE DETECTED (+{avg_r:.3f}R). Proceed to OOS validation.")
    elif avg_r > 0:
        print(f" MARGINAL POSITIVE ({avg_r:+.3f}R). Needs more data or tighter filters.")
    else:
        print(f" NEGATIVE EXPECTANCY ({avg_r:+.3f}R). Strategy needs adjustment.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/backtest_results/combined_backtest_results.csv"
    analyze(filepath)
