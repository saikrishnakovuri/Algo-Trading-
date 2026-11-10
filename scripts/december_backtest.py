import os
import pandas as pd
import numpy as np
import argparse
import logging
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

# Import engines and adapters
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.strategy_selector import StrategySelector, StrategyResult
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter

# Configuration
RISK_PER_TRADE = 5000.0
MAX_WORKERS = 8

def simulate_trade(df, entry_idx, signal):
    """Simulate a trade outcome with granular details."""
    entry = signal.entry
    sl = signal.sl
    target = signal.target1
    direction = signal.direction
    
    risk = abs(entry - sl)
    if risk == 0: return None
    
    outcome = "PENDING"
    r_multiple = 0.0
    exit_price = 0.0
    exit_time = None
    
    # Check up to end of session
    entry_ts = df.index[entry_idx]
    session_end = entry_ts.replace(hour=15, minute=29)
    
    for j in range(entry_idx + 1, len(df)):
        current_ts = df.index[j]
        if current_ts > session_end: break
        
        high = df.iloc[j]['High']
        low = df.iloc[j]['Low']
        
        if direction == "CE":
            if low <= sl:
                outcome = "LOSE"
                r_multiple = -1.0
                exit_price = sl
                exit_time = current_ts
                break
            if high >= target:
                outcome = "WIN"
                r_multiple = (target - entry) / risk
                exit_price = target
                exit_time = current_ts
                break
        else: # PE
            if high >= sl:
                outcome = "LOSE"
                r_multiple = -1.0
                exit_price = sl
                exit_time = current_ts
                break
            if low <= target:
                outcome = "WIN"
                r_multiple = (entry - target) / risk
                exit_price = target
                exit_time = current_ts
                break
                
    if outcome == "PENDING":
        # Force close at EOD
        last_idx = min(len(df)-1, entry_idx + 100) # Safety
        # Find actual last candle of that day
        eod_df = df[df.index.date == entry_ts.date()]
        last_candle = eod_df.iloc[-1]
        exit_price = last_candle['Close']
        exit_time = eod_df.index[-1]
        
        if direction == "CE":
            r_multiple = (exit_price - entry) / risk
        else:
            r_multiple = (entry - exit_price) / risk
        outcome = "WIN" if r_multiple > 0 else "LOSE"
        
    return {
        'date': entry_ts.strftime('%Y-%m-%d'),
        'entry_time': entry_ts.strftime('%H:%M'),
        'exit_time': exit_time.strftime('%H:%M'),
        'symbol': signal.strategy_name, # Strategy name for grouping if needed
        'real_symbol': '', # placeholder
        'strategy': signal.strategy_name,
        'direction': direction,
        'entry': entry,
        'exit': exit_price,
        'pnl': r_multiple * RISK_PER_TRADE,
        'r_multiple': r_multiple,
        'outcome': outcome
    }

def process_single_symbol(args):
    symbol, start_date, end_date = args
    
    # Init engines
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    sr_engine = SweepRetestEngine(config_path="config/sweep_retest.yaml")
    struct_engine = StructureStrategyEngine(config_path="config/structure_strategy.yaml")
    selector = StrategySelector()
    selector.register("MOMENTUM", mom_engine, momentum_adapter)
    selector.register("MEAN_REVERSION", mr_engine, mean_reversion_adapter)
    selector.register("SWEEP_RETEST", sr_engine, sweep_retest_adapter)
    selector.register("STRUCTURE", struct_engine, structure_strategy_adapter)

    all_trades = []
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return []

    try:
        df_raw = pd.read_csv(data_path)
        df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True)
        df_raw.set_index('Timestamp', inplace=True)
        df_raw.sort_index(inplace=True)
        
        # Localize start/end to UTC for comparison
        start_utc = pd.Timestamp(start_date).tz_localize('Asia/Kolkata').tz_convert('UTC')
        end_utc = pd.Timestamp(end_date).tz_localize('Asia/Kolkata').tz_convert('UTC')

        # Filter for December window
        df_full = df_raw[(df_raw.index >= start_utc) & (df_raw.index <= end_utc)]
        if df_full.empty: return []

        # Resample to 5m
        df = df_full.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        if len(df) < 50: return []

        for i in range(50, len(df)):
            df_slice = df.iloc[:i+1]
            # Use COMBINED strategy
            best_sig = selector.select_best(df_slice, symbol, df_1m=df_full.iloc[:i*5])
            if best_sig and best_sig.confidence_pct >= 60:
                trade = simulate_trade(df, i, best_sig)
                if trade:
                    trade['real_symbol'] = symbol
                    all_trades.append(trade)
                    
        return all_trades
    except Exception as e:
        return []

def main():
    # Define December 10-day window (2025-12-01 to 2025-12-12 roughly)
    start_dt = datetime(2025, 12, 1, 9, 15)
    end_dt = datetime(2025, 12, 12, 15, 30)
    
    # 30 Nifty 50 stocks (available in historical)
    nifty_50 = ['ADANIENT', 'ADANIPORTS', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJFINANCE', 'BHARTIARTL', 'HCLTECH', 'HDFCBANK', 'HINDALCO', 'ICICIBANK', 'INDUSINDBK', 'INFY', 'ITC', 'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 'NTPC', 'POWERGRID', 'RELIANCE', 'SBIN', 'SUNPHARMA', 'TATASTEEL', 'TCS', 'TITAN', 'ULTRACEMCO', 'WIPRO']
    
    # We only have 29 stocks total with history. I'll use all 29.
    symbols = nifty_50
    
    print("=" * 105)
    print(f"DECEMBER FINAL BACKTEST | 10 Days (Dec 1 - Dec 12) | {len(symbols)} Stocks | COMBINED STRATEGY")
    print("=" * 105 + "\n")

    args = [(s, start_dt, end_dt) for s in symbols]
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_single_symbol, args))
        
    all_trades = []
    for res in results:
        all_trades.extend(res)

    if not all_trades:
        print("No trades found in this period.")
        return

    df_trades = pd.DataFrame(all_trades)
    
    # 1. Detailed Trade Table (First 30 trades for brevity or all?)
    print("DETAILED TRADES (COMBINED STRATEGY)")
    print("-" * 105)
    header = f"{'Date':<12} | {'Symbol':<10} | {'Strat':<12} | {'Entry':<6} | {'Exit':<6} | {'PnL (INR)':<10} | {'RR':<5} | {'Dir':<3} | {'Outcome':<5}"
    print(header)
    print("-" * 105)
    
    for _, t in df_trades.sort_values(['date', 'entry_time']).iterrows():
        print(f"{t['date']:<12} | {t['real_symbol']:<10} | {t['strategy']:<12} | {t['entry_time']:<6} | {t['exit_time']:<6} | {t['pnl']:<10.2f} | {t['r_multiple']:<5.2f} | {t['direction']:<3} | {t['outcome']:<5}")

    # 2. Daily Summary Table
    print("\n" + "=" * 105)
    print("DAILY PERFORMANCE SUMMARY")
    print("-" * 105)
    print(f"{'Date':<12} | {'Strategy':<12} | {'Trades':<6} | {'Wins':<4} | {'Loss':<4} | {'Win%':<8} | {'PnL (INR)':<12} | {'Profit%'}")
    print("-" * 105)
    
    summary = []
    for d in sorted(df_trades['date'].unique()):
        day_df = df_trades[df_trades['date'] == d]
        for s in ['COMBINED']: # The selector result
            s_df = day_df
            total = len(s_df)
            wins = len(s_df[s_df['outcome'] == 'WIN'])
            losses = len(s_df[s_df['outcome'] == 'LOSE'])
            win_rate = (wins / total * 100) if total > 0 else 0
            pnl = s_df['pnl'].sum()
            # Profit % calculation: (PnL / Total Capital per day). Assume 10L capital.
            profit_pct = (pnl / 1000000.0) * 100
            
            print(f"{d:<12} | {s:<12} | {total:<6} | {wins:<4} | {losses:<4} | {win_rate:<8.1f} | {pnl:<12.2f} | {profit_pct:.2f}%")

    print("=" * 105)

if __name__ == "__main__":
    main()
