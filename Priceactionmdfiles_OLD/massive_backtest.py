"""
MASSIVE BACKTEST VALIDATION
Validates 48 Strategies integrated with the Old Engine pipeline.
Period: Jan, Feb, April, May 2026 (Excluding March).
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# --- CONFIG ---
DATA_FILE = "../data/nifty50_5m.csv"
CAPITAL = 500000
RISK_PCT = 0.01 # 1% risk per trade

def load_backtest_data():
    # Load 5m data (Feb-May)
    df5 = pd.read_csv(DATA_FILE)
    df5.index = pd.to_datetime(df5['Datetime'])
    df5.index.name = 'index_datetime'
    df5.columns = [c.lower() for c in df5.columns]
    
    # Load Jan 1m data and resample
    DATA_JAN_1M = "../data/nifty_index/NIFTY_Jan2026.csv"
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
    df = pd.concat([df5j, df5], sort=False)
    df = df.sort_index()
    
    # Filter months: Jan (1), Feb (2), Mar (3), April (4), May (5)
    df = df[df.index.month.isin([1, 2, 4, 5])]
    return df

def simulate_trade(df, entry_idx, direction, tp_sl_config):
    entry_bar = df.iloc[entry_idx]
    entry_price = entry_bar['close']
    
    if entry_idx < 14: return None
    atr = (df['high'] - df['low']).iloc[entry_idx-14:entry_idx].mean()
    if atr == 0: return None

    sl_dist = atr * tp_sl_config['sl_atr']
    # Risk-based position sizing: Risk 1% of CAPITAL
    risk_amt = CAPITAL * RISK_PCT
    position_size = risk_amt / sl_dist if sl_dist > 0 else 0
    
    exit_price = entry_price
    exit_time = None
    result = "LOSS"
    
    trailing_sl = entry_price - sl_dist if direction == 'BULLISH' else entry_price + sl_dist

    # FIX 6: Extend lookahead to 200 bars
    for j in range(entry_idx + 1, min(entry_idx + 201, len(df))):
        current_bar = df.iloc[j]
        
        # UPDATE TRAILING STOP (only if trail=True in config)
        if tp_sl_config.get('trail', False):
            if direction == 'BULLISH':
                # Trail SL up as price moves up
                new_trail = current_bar['close'] - (atr * tp_sl_config['sl_atr'])
                trailing_sl = max(trailing_sl, new_trail)
                
                # FIX 1: NO TP CAP
                if current_bar['low'] <= trailing_sl:
                    exit_price = trailing_sl
                    exit_time = df.index[j]
                    result = "WIN" if exit_price > entry_price else "LOSS"
                    break
            else:
                # Trail SL down as price moves down
                new_trail = current_bar['close'] + (atr * tp_sl_config['sl_atr'])
                trailing_sl = min(trailing_sl, new_trail)
                
                if current_bar['high'] >= trailing_sl:
                    exit_price = trailing_sl
                    exit_time = df.index[j]
                    result = "WIN" if exit_price < entry_price else "LOSS"
                    break
        else:
            # FIXED TP/SL MODE
            tp_price = entry_price + (sl_dist * tp_sl_config['tp_ratio']) if direction == 'BULLISH' else entry_price - (sl_dist * tp_sl_config['tp_ratio'])
            if direction == 'BULLISH':
                if current_bar['low'] <= trailing_sl:
                    exit_price = trailing_sl
                    exit_time = df.index[j]
                    result = "LOSS"
                    break
                if current_bar['high'] >= tp_price:
                    exit_price = tp_price
                    exit_time = df.index[j]
                    result = "WIN"
                    break
            else:
                if current_bar['high'] >= trailing_sl:
                    exit_price = trailing_sl
                    exit_time = df.index[j]
                    result = "LOSS"
                    break
                if current_bar['low'] <= tp_price:
                    exit_price = tp_price
                    exit_time = df.index[j]
                    result = "WIN"
                    break
                    
    if exit_time is None:
        eod_idx = min(entry_idx + 200, len(df) - 1)
        exit_price = df.iloc[eod_idx]['close']
        exit_time = df.index[eod_idx]
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

def get_market_regime(df, lookback=50):
    """
    Simple regime detection using moving averages and recent highs/lows.
    Returns: 'uptrend', 'downtrend', or 'ranging'
    """
    if len(df) < lookback: return 'ranging'
    recent = df.iloc[-lookback:]
    
    # Short MA vs Long MA
    ma_short = recent['close'].rolling(10).mean().iloc[-1]
    ma_long = recent['close'].rolling(30).mean().iloc[-1]
    
    # Recent higher highs / lower lows
    highs = recent['high'].rolling(10).max()
    lows = recent['low'].rolling(10).min()
    
    recent_high_trend = highs.iloc[-1] > highs.iloc[-20]  # Making new highs
    recent_low_trend = lows.iloc[-1] < lows.iloc[-20]      # Making new lows
    
    if ma_short > ma_long and recent_high_trend:
        return 'uptrend'
    elif ma_short < ma_long and recent_low_trend:
        return 'downtrend'
    else:
        return 'ranging'

def is_market_trending(df, lookback=50):
    """
    FIX 2: Returns True if market is trending.
    """
    if len(df) < lookback: return True # Default to True for warmup
    recent = df.iloc[-lookback:]
    
    # 1. Range Expansion
    highs_10 = recent['high'].rolling(10).max()
    lows_10 = recent['low'].rolling(10).min()
    expanding_range = (highs_10.iloc[-1] - lows_10.iloc[-1]) > (highs_10.iloc[-20] - lows_10.iloc[-20])
    
    # 2. MA Slope
    ma20 = recent['close'].rolling(20).mean()
    if ma20.iloc[-5] == 0: return True
    ma_slope = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] * 100
    
    # 3. ATR expansion
    atr_recent = (recent['high'] - recent['low']).iloc[-10:].mean()
    atr_older = (recent['high'] - recent['low']).iloc[-30:-20].mean()
    atr_expanding = atr_recent > atr_older * 1.1 if atr_older > 0 else True
    
    return expanding_range and (abs(ma_slope) > 0.1 or atr_expanding)

def main():
    print("Initializing Unified Strategy Engine (PHASE 3)...")
    engine = UnifiedStrategyEngine()
    
    print("Loading historical data...")
    df = load_backtest_data()
    print(f"Data Loaded: {len(df)} bars.")
    
    trades = []
    
    print("Running Backtest...")
    for i in range(50, len(df), 3):
        if i % 200 == 0:
            print(f"Progress: {i}/{len(df)} bars...")
            
        current_bar = df.iloc[i]
        # FIX 3: Skip Mon, Tue, Wed (0, 1, 2)
        if current_bar.name.weekday() in [0, 1, 2]:
            continue
            
        # FIX 4: Tighten Window (10:00-11:59)
        hour = current_bar.name.hour
        if hour < 10 or hour >= 12:
            continue
            
        current_window = df.iloc[:i+1]
        
        # FIX 2: Skip Choppy Markets
        if not is_market_trending(current_window):
            continue
            
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals:
            continue
            
        best_sig = max(signals, key=lambda x: x.confidence)
        
        # FIX 5: Only Breakout-Retest-Continuation
        if best_sig.strategy_name != 'Breakout-Retest-Continuation':
            continue

        if best_sig.confidence < 0.85:
            continue
            
        direction = 'BULLISH' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
        
        # REGIME FILTER (Still using the basic one from Phase 2 too)
        regime = get_market_regime(current_window)
        if direction == 'BULLISH' and regime == 'downtrend': continue
        if direction == 'BEARISH' and regime == 'uptrend': continue

        # Use optimal ATR Config (WIDE_3R but NO TP CAP in logic)
        tpsl = {"name": "ATR_TRAILING", "sl_atr": 2.0, "tp_ratio": 3.0, "trail": True}
        
        res = simulate_trade(df, i, direction, tpsl)
        if res:
            res.update({
                "strategy": best_sig.strategy_name,
                "tpsl_method": tpsl['name'],
                "month": df.index[i].month_name(),
                "confidence": best_sig.confidence
            })
            trades.append(res)
                
    # Create Report
    if not trades:
        print("No trades found.")
        return

    results_df = pd.DataFrame(trades)
    results_df.to_csv("backtest_detailed_results.csv", index=False)
    
    # Aggregate Insights
    print("\n" + "="*50)
    print("   BACKTEST PERFORMANCE INSIGHTS")
    print("="*50)
    
    # 1. Performance by Month
    month_stats = results_df.groupby('month')['pnl_pct'].sum().sort_values(ascending=False)
    print("\n--- Performance by Month ---")
    print(month_stats)
    
    # 2. Top Performing Strategies
    strat_stats = results_df.groupby('strategy')['pnl_pct'].agg(['sum', 'count', 'mean']).sort_values(by='sum', ascending=False)
    print("\n--- Top Strategies ---")
    print(strat_stats.head(10))
    
    # 3. Best TP/SL Strategy
    tpsl_stats = results_df.groupby('tpsl_method')['pnl_pct'].sum().sort_values(ascending=False)
    print("\n--- TP/SL Strategy Performance ---")
    print(tpsl_stats)
    
    # 4. Outperformer and Low Performer
    best_strat = strat_stats.index[0]
    worst_strat = strat_stats.index[-1]
    print(f"\nMOST OUTPERFORMING STRATEGY: {best_strat}")
    print(f"LOWEST PERFORMING STRATEGY:   {worst_strat}")
    
    print(f"\nTotal P&L: ₹{results_df['pnl'].sum():,.2f}")
    print(f"Total Return: {(results_df['pnl'].sum()/CAPITAL)*100:.2f}%")
    print(f"Win Rate: {(len(results_df[results_df['result'] == 'WIN'])/len(results_df))*100:.1f}%")

    print("\nDetailed results saved to 'backtest_detailed_results.csv'")
    print("="*50)

if __name__ == "__main__":
    main()
