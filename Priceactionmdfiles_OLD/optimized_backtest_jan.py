
import pandas as pd
import numpy as np
import os
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# --- CONFIG ---
DATA_FILE_JAN = "../data/nifty_index/NIFTY_Jan2026.csv"
CAPITAL = 500000
RISK_PCT = 0.01

# BLACKLISTED STRATEGIES
BLACKLIST = [
    "Ascending Triangle",
    "Higher High & Higher Low",
    "Descending Channel",
    "Lower High & Lower Low"
]

def load_data():
    print(f"Loading January data from {DATA_FILE_JAN}...")
    df1j = pd.read_csv(DATA_FILE_JAN)
    df1j.index = pd.to_datetime(df1j['Timestamp'])
    df1j.columns = [c.lower() for c in df1j.columns]
    
    # Resample to 5m
    df = df1j.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df.index.name = 'index_datetime'
    
    # Filter: Exclude Monday (0) and Tuesday (1)
    df = df[~df.index.weekday.isin([0, 1])]
    
    # Filter: Exclude Time Windows
    df = df[~((df.index.hour == 9) & (df.index.minute < 45))]
    df = df[~((df.index.hour == 15) & (df.index.minute <= 15))]
    
    return df

def simulate_trade(df, entry_idx, direction):
    entry_bar = df.iloc[entry_idx]
    entry_price = entry_bar['close']
    
    if entry_idx < 14: return None
    # Calculate ATR manually for consistency
    sub_df = df.iloc[entry_idx-14:entry_idx]
    tr = pd.concat([
        sub_df['high'] - sub_df['low'],
        (sub_df['high'] - sub_df['close'].shift(1)).abs(),
        (sub_df['low'] - sub_df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.mean()
    
    if atr == 0: return None

    # ATR_TRAILING Parameters
    sl_atr_mult = 2.0
    tp_atr_mult = 5.0 # High target, relies on trailing
    
    sl_dist = atr * sl_atr_mult
    risk_amt = CAPITAL * RISK_PCT
    position_size = risk_amt / sl_dist if sl_dist > 0 else 0
    
    if direction == 'BULLISH':
        sl_price = entry_price - sl_dist
        tp_price = entry_price + (atr * tp_atr_mult)
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - (atr * tp_atr_mult)
        
    exit_price = entry_price
    exit_time = None
    result = "LOSS"
    
    # Trailing Logic
    current_sl = sl_price
    
    for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
        current_bar = df.iloc[j]
        
        if direction == 'BULLISH':
            # Trail SL
            if current_bar['close'] > entry_price + atr:
                new_sl = current_bar['close'] - (atr * 1.5)
                current_sl = max(current_sl, new_sl)
            
            if current_bar['low'] <= current_sl:
                exit_price = current_sl
                exit_time = df.index[j]
                result = "WIN" if exit_price > entry_price else "LOSS"
                break
            if current_bar['high'] >= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                break
        else: # BEARISH
            # Trail SL
            if current_bar['close'] < entry_price - atr:
                new_sl = current_bar['close'] + (atr * 1.5)
                current_sl = min(current_sl, new_sl)
                
            if current_bar['high'] >= current_sl:
                exit_price = current_sl
                exit_time = df.index[j]
                result = "WIN" if exit_price < entry_price else "LOSS"
                break
            if current_bar['low'] <= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                break
                    
    if exit_time is None:
        exit_price = df.iloc[min(entry_idx + 100, len(df)-1)]['close']
        exit_time = df.index[min(entry_idx + 100, len(df)-1)]
        result = "EOD"
        
    price_change = (exit_price - entry_price) if direction == 'BULLISH' else (entry_price - exit_price)
    actual_pnl = price_change * position_size
    
    return {
        "entry_time": df.index[entry_idx],
        "exit_time": exit_time,
        "result": result,
        "pnl": actual_pnl,
        "pnl_pct": (actual_pnl / CAPITAL) * 100
    }

def main():
    print("Initializing Optimized Unified Strategy Engine...")
    engine = UnifiedStrategyEngine()
    df = load_data()
    print(f"Data Loaded and Filtered: {len(df)} bars.")
    
    trades = []
    for i in range(50, len(df), 3):
        if i % 200 == 0: print(f"Progress: {i}/{len(df)} bars...")
            
        current_window = df.iloc[:i+1]
        # PASS backtest_mode=True to ensure regime fallback works
        signals = engine.get_signals(current_window, backtest_mode=True)
        
        if not signals: continue
            
        # Filter signals based on BLACKLIST
        signals = [s for s in signals if s.strategy_name not in BLACKLIST]
        if not signals: continue
            
        best_sig = max(signals, key=lambda x: x.confidence)
        
        direction = 'BULLISH' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
        res = simulate_trade(df, i, direction)
        if res:
            res.update({
                "strategy": best_sig.strategy_name,
                "month": df.index[i].month_name(),
                "confidence": best_sig.confidence
            })
            trades.append(res)
                
    results_df = pd.DataFrame(trades)
    results_df.to_csv("optimized_backtest_results_jan.csv", index=False)
    
    print("\n" + "="*50)
    print("   OPTIMIZED BACKTEST RESULTS (JANUARY 2026)")
    print("="*50)
    print(f"Total Trades: {len(results_df)}")
    if not results_df.empty:
        print(f"Total Absolute P&L: ₹{results_df['pnl'].sum():.2f}")
        print(f"Total Portfolio Return: {(results_df['pnl'].sum()/CAPITAL)*100:.2f}%")
        
        wins = len(results_df[results_df['result'] == 'WIN'])
        losses = len(results_df[results_df['result'] == 'LOSS'])
        print(f"Win Rate: {(wins/(wins+losses)*100):.2f}%" if (wins+losses) > 0 else "N/A")
        
        print("\n--- Top Performing Strategies ---")
        print(results_df.groupby('strategy')['pnl'].sum().sort_values(ascending=False).head(5))
    else:
        print("No trades found for January with current filters.")
    print("="*50)

if __name__ == "__main__":
    main()
