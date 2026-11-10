import sys, os
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.ERROR)

from modules.strategy_selector import MasterStrategySelector
from main_backtest import load_data, resample_5m, simulate_trade
from modules.indicator_cache import precompute_indicators
from modules.v3_utils import TOTAL_CAPITAL

symbols = ["ADANIENT", "BAJFINANCE", "MPHASIS", "GODREJPROP", "AUROPHARMA"]
start_date = pd.Timestamp("2026-04-21").tz_localize('Asia/Kolkata')
end_date = pd.Timestamp("2026-05-20").tz_localize('Asia/Kolkata')

print(f"Running 30-Day Backtest for Candlestick S/R Analysis on: {', '.join(symbols)}")

master = MasterStrategySelector()
candlestick_trades = []

for symbol in symbols:
    df_full = load_data(symbol)
    if df_full is None: continue
    
    df_1m = df_full[(df_full.index >= start_date) & (df_full.index <= end_date)]
    if df_1m.empty: continue
    
    df_5m = resample_5m(df_1m)
    df_5m = precompute_indicators(df_5m)
    
    i = 50
    while i < len(df_5m):
        sub_df = df_5m.iloc[:i+1]
        now = sub_df.index[-1]
        risk_amt = TOTAL_CAPITAL * 0.01
        
        signal = master.select_best_signal(sub_df, symbol, 15.0, current_time=now)
        
        if signal:
            trade = simulate_trade(df_5m.iloc[i], df_5m.iloc[i:], risk_amt, signal, symbol)
            if signal['strategy'] == 'CANDLESTICK':
                trade['structure'] = signal['context'].structure
                candlestick_trades.append(trade)
            i += trade['exit_idx'] + 1
        else:
            i += 1

df_trades = pd.DataFrame(candlestick_trades)
if df_trades.empty:
    print("\nNo Candlestick trades generated for these 5 stocks.")
else:
    print("\n=== CANDLESTICK TRADES BY MARKET STRUCTURE ===")
    stats = []
    for structure, group in df_trades.groupby('structure'):
        pnls = group['net_pnl'].tolist()
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        wr = len(wins) / len(pnls) * 100
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
        stats.append({
            'Structure Context': structure,
            'Trades': len(pnls),
            'Wins': len(wins),
            'Losses': len(losses),
            'Win Rate': f"{wr:.1f}%",
            'Net P&L': f"₹ {sum(pnls):,.2f}",
            'Profit Factor': f"{pf:.2f}"
        })
    print(pd.DataFrame(stats).to_markdown(index=False))

    print("\n=== INDIVIDUAL CANDLESTICK TRADES ===")
    cols = ['timestamp', 'symbol', 'direction', 'structure', 'net_pnl']
    print(df_trades[cols].to_markdown(index=False))
