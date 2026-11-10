import json
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime

def analyze_paper_trades(since_date=None):
    trades_file = Path("data/paper_trades.jsonl")
    if not trades_file.exists():
        print("No paper trade data found.")
        return

    trades = []
    with open(trades_file, 'r') as f:
        for line in f:
            trades.append(json.loads(line))
    
    df = pd.DataFrame(trades)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    if since_date:
        df = df[df['timestamp'] >= pd.to_datetime(since_date)]

    if df.empty:
        print("No trades in selected window.")
        return

    # Metrics
    total = len(df)
    net_pnl = df['net_pnl'].sum()
    wr = (df['net_pnl'] > 0).mean() * 100
    wins = df[df['net_pnl'] > 0]['net_pnl'].sum()
    losses = abs(df[df['net_pnl'] <= 0]['net_pnl'].sum())
    pf = wins / losses if losses > 0 else float('inf')
    cum_pnl = df['net_pnl'].cumsum()
    max_dd = (cum_pnl - cum_pnl.cummax()).min()

    print(f"Total Trades: {total}")
    print(f"WR: {wr:.1f}%")
    print(f"Net PnL: {net_pnl:,.0f}")
    print(f"PF: {pf:.2f}")
    print(f"Max DD: {max_dd:,.0f}")

    print("\nPer-Strategy Breakdown:")
    strat = df.groupby('strategy')['net_pnl'].agg(['count', 'sum', lambda x: (x>0).mean()*100])
    print(strat.rename(columns={'count': 'trades', 'sum': 'pnl', '<lambda_0>': 'wr%'}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default=None)
    args = parser.parse_args()
    analyze_paper_trades(args.since)
