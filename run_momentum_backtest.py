#!/usr/bin/env python3
"""Momentum Breakout Backtest Runner"""

import pandas as pd
import numpy as np
import argparse
import os
from datetime import datetime, time as dtime
from modules.momentum_engine import MomentumBreakoutEngine

def execute_trade(df, entry_idx, signal, interval_str):
    """
    Executes a trade and tracks it until exit.
    Adapted from backtest_engine.py logic.
    """
    data_interval_minutes = 1 if interval_str == "1m" else 5
    symbol = "UNKNOWN" # Could be passed in if needed
    
    # Trigger price and entry
    # For breakout, we assume entry is at the signal close (as per signal engine)
    entry = signal['entry']
    original_sl = signal['sl']
    target = signal['target1']
    trade_type = signal['direction'] # 'CE' or 'PE'
    
    # Slippage Model (Liquid Stocks)
    slippage_factor = 0.0005 # 5 bps
    entry = entry + (entry * slippage_factor) if trade_type == 'CE' else entry - (entry * slippage_factor)
    
    dist_to_sl = abs(entry - original_sl)
    if dist_to_sl == 0: return None
    
    # Trigger Breakeven once RR 1.0:1 is achieved
    rr_trigger = entry + (dist_to_sl * 1.0) if trade_type == 'CE' else entry - (dist_to_sl * 1.0)
    
    sl = original_sl
    hit_breakeven = False
    exit_price = None
    outcome = "OPEN"
    
    # Future data for trade tracking (max 1 day)
    lookahead = 240 if interval_str == "1m" else 75
    trade_future = df.iloc[entry_idx + 1 : entry_idx + lookahead]
    
    if trade_future.empty:
        return None

    # Position Sizing (Simple 100k equity base for calculation)
    current_equity = 100000.0
    risk_pct = 0.01 if signal['score'] >= 8.5 else 0.005
    risk_per_trade = current_equity * risk_pct
    qty = int(risk_per_trade / dist_to_sl) if dist_to_sl > 0 else 0
    if qty == 0: return None

    for bars_passed, (_, row) in enumerate(trade_future.iterrows()):
        curr_low = float(row["Low"])
        curr_high = float(row["High"])
        curr_close = float(row["Close"])

        dist = (curr_close - entry) if trade_type == 'CE' else (entry - curr_close)
        current_r = dist / dist_to_sl
        
        elapsed_minutes = (bars_passed + 1) * data_interval_minutes

        # GRADUATED TIME MANAGEMENT
        if elapsed_minutes >= 20 and current_r < 0:
            outcome = "TIME_CUT_20M_LOSING"; exit_price = curr_close; break
        if elapsed_minutes >= 45 and not hit_breakeven:
            if 0 < current_r < 0.5:
                sl = entry; hit_breakeven = True
            elif current_r <= 0:
                outcome = "TIME_CUT_45M_STALLED"; exit_price = curr_close; break
        if elapsed_minutes >= 90 and current_r < 1.0:
            outcome = "TIME_CUT_90M_FINAL"; exit_price = curr_close; break
        if elapsed_minutes >= 150:
            outcome = "TIME_CUT_EOD"; exit_price = curr_close; break
        
        # Breakeven Move
        if not hit_breakeven:
            if (trade_type == "CE" and curr_high >= rr_trigger) or \
               (trade_type == "PE" and curr_low <= rr_trigger):
                sl = entry; hit_breakeven = True

        # SL / Target Hit
        if trade_type == "CE":
            if curr_low <= sl: 
                outcome = "BREAKEVEN" if hit_breakeven else "SL HIT"; exit_price = sl; break
            if curr_high >= target: 
                outcome = "TARGET HIT"; exit_price = target; break
        else:
            if curr_high >= sl: 
                outcome = "BREAKEVEN" if hit_breakeven else "SL HIT"; exit_price = sl; break
            if curr_low <= target: 
                outcome = "TARGET HIT"; exit_price = target; break
                
    if exit_price is None:
        exit_price = float(trade_future.iloc[-1]['Close'])
        outcome = "FORCE_CLOSE_EOD"

    # Exit Slippage
    is_market_exit = outcome not in ["TARGET HIT", "SL HIT"]
    if is_market_exit:
        exit_price = exit_price - (exit_price * slippage_factor) if trade_type == 'CE' else exit_price + (exit_price * slippage_factor)

    pnl = (exit_price - entry) * qty if trade_type == 'CE' else (entry - exit_price) * qty
    
    return {
        "date": str(df.index[entry_idx]),
        "type": trade_type,
        "entry": round(entry, 2),
        "exit": round(exit_price, 2),
        "qty": qty,
        "pnl": round(pnl, 2),
        "outcome": outcome,
        "score": signal['score'],
        "r_multiple": round(pnl / (dist_to_sl * qty), 2) if qty > 0 else 0
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=[
        "RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "SBIN",
        "BAJFINANCE", "KOTAKBANK", "AXISBANK", "MARUTI", "INFY"
    ])
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--interval", default="5m", choices=["1m", "5m"])
    parser.add_argument("--target-r", type=float, default=1.5)
    parser.add_argument("--threshold", type=float, default=5.0)
    parser.add_argument("--start-date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--step-size", type=int, default=1, help="Step size for bars")
    args = parser.parse_args()
    
    engine = MomentumBreakoutEngine()
    trades = []
    
    for symbol in args.symbols:
        suffix = "_1m.csv" if args.interval == "1m" else "_5m.csv"
        filepath = f"data/extended/{symbol}{suffix}"
        if not os.path.exists(filepath):
            filepath = f"data/angel_historical/{symbol}{suffix}"
        if not os.path.exists(filepath):
            print(f"Skipping {symbol}: no data file found")
            continue
        
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            
            if args.start_date:
                df = df[df.index >= args.start_date]
            if args.end_date:
                df = df[df.index <= args.end_date]
                
            if df.empty:
                print(f"Skipping {symbol}: no data in date range")
                continue
                
            print(f"Processing {symbol}: {len(df)} bars")
            
            # Use step_size for signal generation
            for i in range(30, len(df), args.step_size):
                df_slice = df.iloc[:i+1]
                
                signal = engine.generate_signal(
                    df_slice, symbol, 
                    config={'target_r': args.target_r}
                )
                
                if signal.get('signal') and signal.get('score', 0) >= args.threshold:
                    # Execute trade
                    trade_result = execute_trade(
                        df, i, signal, args.interval
                    )
                    if trade_result:
                        trade_result['symbol'] = symbol
                        trades.append(trade_result)
                        # Jump forward to skip the bars of the trade
                        # (Simulating one trade at a time for simplicity in this runner)
                        # i += 10 # Optional: simple skip
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    # Print summary
    if trades:
        df_trades = pd.DataFrame(trades)
        wins = len(df_trades[df_trades['pnl'] > 0])
        total = len(df_trades)
        total_pnl = df_trades['pnl'].sum()
        
        # Calculate RR Ratio based on R-multiples
        avg_r = df_trades['r_multiple'].mean()
        
        print(f"\n{'='*50}")
        print(f"MOMENTUM BREAKOUT RESULTS")
        print(f"{'='*50}")
        print(f"Total Trades: {total}")
        print(f"Wins: {wins}")
        print(f"Win Rate: {wins/total*100:.1f}%")
        print(f"Avg R-Multiple: {avg_r:.3f}R")
        print(f"Total P&L: {total_pnl:.2f}")
        
        df_trades.to_csv("trade_journal_momentum.csv", index=False)
        print(f"Journal saved to trade_journal_momentum.csv")
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    main()
