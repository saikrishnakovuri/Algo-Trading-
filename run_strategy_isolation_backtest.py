#!/usr/bin/env python3
"""Strategy Isolation Backtest — runs once, slices by setup_type."""

import os
import sys
import pandas as pd
import json
from datetime import datetime
from backtest_engine import BacktestEngine

def run_full_backtest():
    """Run the main backtest and return the trade journal."""
    print("=" * 60)
    print("RUNNING FULL BACKTEST (all strategies, all stocks)")
    print("=" * 60)
    
    data_dir = "data/angel_historical"
    top_10_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_10_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])

    session_id = f"full_iso_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    journal_file = f"trade_journal_isolation.csv"
    
    # Reset journal
    if os.path.exists(journal_file):
        os.remove(journal_file)
        
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file
    
    trades = engine.run_massive_backtest_v2(all_files)
    
    if not trades:
        print("❌ No trades generated.")
        return pd.DataFrame()
        
    df = pd.DataFrame(trades)
    
    # Calculate R-multiple if not present
    # risk = abs(entry - sl)
    # r_multiple = pnl / (risk * qty)
    def calc_r(row):
        risk = abs(row['entry'] - row['sl'])
        if risk <= 0 or row['qty'] <= 0: return 0
        return round(row['pnl'] / (risk * row['qty']), 2)
        
    df['r_multiple'] = df.apply(calc_r, axis=1)
    return df

def compute_metrics(df, label="ALL"):
    """Compute standard metrics for a set of trades."""
    if len(df) == 0:
        return {
            "strategy": label, "trades": 0, "wins": 0, "losses": 0,
            "win_pct": "0.0%", "avg_win_r": 0, 
            "avg_loss_r": 0, "expectancy_r": 0,
            "profit_factor": 0, "pnl_inr": 0,
            "max_dd_pct": "0.0%", "top_exit_reason": "N/A"
        }
    
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] < 0]
    
    total = len(df)
    win_count = len(wins)
    loss_count = len(losses)
    win_pct = round(win_count / total * 100, 1) if total > 0 else 0
    
    avg_win_r = round(wins['r_multiple'].mean(), 2) if len(wins) > 0 else 0
    avg_loss_r = round(abs(losses['r_multiple'].mean()), 2) if len(losses) > 0 else 1.0
    
    expectancy = round(
        (win_pct/100 * avg_win_r) - ((100-win_pct)/100 * avg_loss_r), 3
    )
    
    gross_win = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 1
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else 99.0
    
    total_pnl = round(df['pnl'].sum(), 2)
    
    # Max drawdown from cumulative P&L
    cum_pnl = df['pnl'].cumsum()
    running_max = cum_pnl.cummax()
    dd = cum_pnl - running_max
    max_dd = round(abs(dd.min()) / 1000000 * 100, 2)  # as % of 10L capital
    
    # Exit reason distribution (outcome in our journal)
    top_exit = df['outcome'].mode().iloc[0] if 'outcome' in df.columns and len(df) > 0 else "N/A"
    
    return {
        "strategy": label,
        "trades": total,
        "wins": win_count,
        "losses": loss_count,
        "win_pct": f"{win_pct}%",
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "expectancy_r": expectancy,
        "profit_factor": pf,
        "pnl_inr": total_pnl,
        "max_dd_pct": f"{max_dd}%",
        "top_exit_reason": top_exit
    }

def print_table(results):
    """Print formatted comparison table."""
    print("\n" + "=" * 125)
    print("║" + " STRATEGY ISOLATION PERFORMANCE SUMMARY ".center(123) + "║")
    print("=" * 125)
    header = f"║ {'Strategy':<20} ║ {'Trades':>6} ║ {'Wins':>4} ║ {'Loss':>4} ║ {'Win%':>6} ║ {'AvgW(R)':>7} ║ {'AvgL(R)':>7} ║ {'Expect(R)':>9} ║ {'PF':>5} ║ {'P&L(INR)':>10} ║ {'MaxDD%':>6} ║"
    print(header)
    print("╠" + "═"*22 + "╬" + "═"*8 + "╬" + "═"*6 + "╬" + "═"*6 + "╬" + "═"*8 + "╬" + "═"*9 + "╬" + "═"*9 + "╬" + "═"*11 + "╬" + "═"*7 + "╬" + "═"*12 + "╬" + "═"*8 + "╣")
    
    for r in results:
        line = f"║ {r['strategy']:<20} ║ {r['trades']:>6} ║ {r['wins']:>4} ║ {r['losses']:>4} ║ {r['win_pct']:>6} ║ {r['avg_win_r']:>7} ║ {r['avg_loss_r']:>7} ║ {r['expectancy_r']:>9} ║ {r['profit_factor']:>5} ║ {r['pnl_inr']:>10.0f} ║ {r['max_dd_pct']:>6} ║"
        print(line)
    
    print("╚" + "═"*22 + "╩" + "═"*8 + "╩" + "═"*6 + "╩" + "═"*6 + "╩" + "═"*8 + "╩" + "═"*9 + "╩" + "═"*9 + "╩" + "═"*11 + "╩" + "═"*7 + "╩" + "═"*12 + "╩" + "═"*8 + "╝")

def main():
    df = run_full_backtest()
    if df.empty: return
    
    # Use 'setup' column from journal
    type_col = 'setup'
    
    strategies = df[type_col].unique()
    results = []
    for strat in sorted(strategies):
        strat_df = df[df[type_col] == strat].copy()
        metrics = compute_metrics(strat_df, label=strat)
        results.append(metrics)
    
    # Add combined row
    combined = compute_metrics(df, label="COMBINED (all)")
    results.append(combined)
    
    # Print table
    print_table(results)
    
    # Ranking
    ranked = sorted(
        [r for r in results if r['strategy'] != 'COMBINED (all)'],
        key=lambda x: x['expectancy_r'] if isinstance(x['expectancy_r'], (int, float)) else -999,
        reverse=True
    )
    
    print("\nRANKED BY EXPECTANCY:")
    for i, r in enumerate(ranked, 1):
        status = "KEEP" if r['expectancy_r'] > 0 and r['profit_factor'] > 1.0 else "DISABLE"
        if r['trades'] < 5: status = "REVIEW (Low Sample)"
        print(f"  {i}. {r['strategy']:<18} Exp: {r['expectancy_r']:>7}R  PF: {r['profit_factor']:>5}  Trades: {r['trades']:>3}  -> {status}")

    # Per-stock for top 2
    top_strats = [r['strategy'] for r in ranked[:2] if r['trades'] >= 3]
    for strat_name in top_strats:
        print(f"\nPER-STOCK: {strat_name}")
        s_df = df[df[type_col] == strat_name]
        sym_results = []
        for sym in sorted(s_df['symbol'].unique()):
            sym_df = s_df[s_df['symbol'] == sym]
            sym_results.append(compute_metrics(sym_df, sym))
        
        # Simple print
        for m in sym_results:
            print(f"  {m['strategy']:<12}: Trades {m['trades']:>2} | Win% {m['win_pct']:>5} | Exp {m['expectancy_r']:>6}R | P&L {m['pnl_inr']:>8}")

    # Save
    pd.DataFrame(results).to_csv("data/strategy_isolation_summary.csv", index=False)
    print("\n✅ Results saved to data/strategy_isolation_summary.csv")

if __name__ == "__main__":
    main()
