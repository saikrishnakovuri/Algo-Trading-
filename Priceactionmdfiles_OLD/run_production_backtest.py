
import pandas as pd
import numpy as np
import os
from datetime import datetime
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# Paths
DATA_5M = "../data/nifty50_5m.csv"
DATA_JAN_1M = "../data/nifty_index/NIFTY_Jan2026.csv"
OUTPUT_FILE = "backtest_detailed_results.csv"

# Config
INITIAL_CAPITAL = 500000.0
RISK_PER_TRADE = 0.01  # 1%
ATR_PERIOD = 14
ATR_MULTIPLIER_SL = 1.5

def load_and_combine_data():
    print("Loading data...")
    # Load 5m data (Feb-May)
    df5 = pd.read_csv(DATA_5M)
    df5.index = pd.to_datetime(df5['Datetime'])
    df5.index.name = 'index_datetime'
    df5.columns = [c.lower() for c in df5.columns]
    
    # Load Jan 1m data and resample
    df1j = pd.read_csv(DATA_JAN_1M)
    df1j.index = pd.to_datetime(df1j['Timestamp'])
    df1j.index.name = 'index_datetime'
    df1j.columns = [c.lower() for c in df1j.columns]
    
    df5j = df1j.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Combine
    df = pd.concat([df5j, df5])
    df = df.sort_index()
    
    # EXCLUDE March
    df = df[df.index.month != 3]
    
    # EXCLUDE Monday (0) and Tuesday (1)
    df = df[~df.index.weekday.isin([0, 1])]
    
    # Drop duplicates if any
    df = df[~df.index.duplicated(keep='first')]
    
    print(f"Total data points after day filters: {len(df)}")
    return df

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_prev_close = (df['high'] - df['close'].shift(1)).abs()
    low_prev_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def is_vetoed(df, idx, direction, strategy_score, entry_time):
    # Time Window Vetoes
    h, m = entry_time.hour, entry_time.minute
    
    # 9:15-09:45 AM
    if h == 9 and m < 45:
        return True, "Opening Burst Veto"
        
    # 3:00-3:15 PM (15:00-15:15)
    if h == 15 and m <= 15:
        return True, "EOD Blackout Veto"
        
    # Momentum Veto: Only trade if last 3 closes are aligned with direction
    if idx < 3: return True, "Insufficient Momentum Data"
    last_closes = df['close'].iloc[idx-2:idx+1].values
    if direction == 'BULLISH':
        if not (last_closes[2] > last_closes[0]):
            return True, "Momentum Veto (Not Bullish)"
    else:
        if not (last_closes[2] < last_closes[0]):
            return True, "Momentum Veto (Not Bearish)"
            
    # Afternoon CE Veto: Block CE after 1:30 PM (13:30) if score < 7.5
    # Since confidence is 0-1, we use 0.75
    if direction == 'BULLISH' and (h > 13 or (h == 13 and m >= 30)):
        if strategy_score < 0.75:
            return True, "Afternoon CE Veto (Low Score)"
            
    return False, None

def simulate_atr_trailing_trade(df, entry_idx, direction, confidence):
    entry_price = df.iloc[entry_idx]['close']
    entry_time = df.index[entry_idx]
    
    # Calculate ATR at entry
    atr_series = calculate_atr(df.iloc[:entry_idx+1])
    atr = atr_series.iloc[-1]
    if pd.isna(atr) or atr == 0:
        atr = entry_price * 0.001 # Fallback
        
    initial_sl_dist = ATR_MULTIPLIER_SL * atr
    
    if direction == 'BULLISH':
        sl = entry_price - initial_sl_dist
        tp = entry_price + (initial_sl_dist * 3) # 3R Target for baseline
    else:
        sl = entry_price + initial_sl_dist
        tp = entry_price - (initial_sl_dist * 3)
        
    # Trailing SL logic
    # Initial trailing: moves up with price if BULLISH
    current_sl = sl
    
    # Position Sizing
    risk_amt = INITIAL_CAPITAL * RISK_PER_TRADE
    qty = int(risk_amt / initial_sl_dist) if initial_sl_dist > 0 else 0
    if qty == 0: return None
    
    # Simulate forward (max 100 bars or end of day)
    exit_idx = -1
    exit_price = 0
    outcome = "LOSS"
    
    # End of day time (approx 15:25)
    eod_time = 15 * 3600 + 25 * 60
    
    for j in range(entry_idx + 1, len(df)):
        row = df.iloc[j]
        curr_time_sec = row.name.hour * 3600 + row.name.minute * 60
        
        # Check EOD
        if curr_time_sec >= eod_time:
            exit_idx = j
            exit_price = row['close']
            outcome = "EOD"
            break
            
        if direction == 'BULLISH':
            # Update Trailing SL: 1.5 ATR from HIGH
            new_sl = row['high'] - initial_sl_dist
            if new_sl > current_sl:
                current_sl = new_sl
            
            if row['low'] <= current_sl:
                exit_idx = j
                exit_price = current_sl
                outcome = "WIN" if exit_price > entry_price else "LOSS"
                break
            if row['high'] >= tp:
                exit_idx = j
                exit_price = tp
                outcome = "WIN"
                break
        else:
            # Update Trailing SL: 1.5 ATR from LOW
            new_sl = row['low'] + initial_sl_dist
            if new_sl < current_sl:
                current_sl = new_sl
                
            if row['high'] >= current_sl:
                exit_idx = j
                exit_price = current_sl
                outcome = "WIN" if exit_price < entry_price else "LOSS"
                break
            if row['low'] <= tp:
                exit_idx = j
                exit_price = tp
                outcome = "WIN"
                break
                
    if exit_idx == -1:
        exit_idx = len(df) - 1
        exit_price = df.iloc[-1]['close']
        outcome = "EOD"
        
    pnl = (exit_price - entry_price) * qty if direction == 'BULLISH' else (entry_price - exit_price) * qty
    pnl_pct = (pnl / INITIAL_CAPITAL) * 100
    
    return {
        'entry_time': entry_time,
        'exit_time': df.index[exit_idx],
        'result': outcome,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'strategy': 'Unknown',
        'month': entry_time.strftime('%B'),
        'confidence': confidence
    }

def main():
    df = load_and_combine_data()
    engine = UnifiedStrategyEngine()
    
    trades = []
    
    print("Running production backtest...")
    # Start from index 100 for indicator stability
    for i in range(100, len(df), 3):
        if i % 500 == 0:
            print(f"Progress: {i}/{len(df)} bars...")
            
        row = df.iloc[i]
        current_window = df.iloc[:i+1]
        
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals:
            continue
            
        # Select best signal
        best_sig = max(signals, key=lambda x: x.confidence)
        
        direction = 'BULLISH' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
        
        # Apply Vetoes
        vetoed, reason = is_vetoed(df, i, direction, best_sig.confidence, row.name)
        if vetoed:
            continue
            
        trade = simulate_atr_trailing_trade(df, i, direction, best_sig.confidence)
        if trade:
            trade['strategy'] = best_sig.strategy_name
            trades.append(trade)
            
    if trades:
        results_df = pd.DataFrame(trades)
        results_df.to_csv(OUTPUT_FILE, index=False)
        
        print("\n" + "="*50)
        print("PRODUCTION BACKTEST RESULTS")
        print("="*50)
        print(f"Total Trades:  {len(results_df)}")
        print(f"Total PnL:     {results_df['pnl'].sum():.2f}")
        print(f"Win Rate:      {(results_df['result'] == 'WIN').mean()*100:.2f}%")
        
        # Monthly breakdown
        print("\nMonthly Performance:")
        print(results_df.groupby('month')['pnl'].sum())
        
        # Top Strategies
        print("\nTop 5 Strategies:")
        print(results_df.groupby('strategy')['pnl'].sum().sort_values(ascending=False).head(5))
        print("="*50)
    else:
        print("No trades found.")

if __name__ == "__main__":
    main()
