
import pandas as pd
import numpy as np
import os
from datetime import datetime
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# --- CONFIG ---
DATA_FILE = "../data/nifty50_5m.csv"
DATA_JAN_1M = "../data/nifty_index/NIFTY_Jan2026.csv"
CAPITAL = 500000
RISK_PCT = 0.01

ATR_CONFIGS = [
    {"sl_atr": 1.0, "tp_ratio": 3.0, "trail": True, "name": "TIGHT_3R"},
    {"sl_atr": 1.5, "tp_ratio": 3.0, "trail": True, "name": "MED_3R"},
    {"sl_atr": 1.5, "tp_ratio": 4.0, "trail": True, "name": "MED_4R"},
    {"sl_atr": 2.0, "tp_ratio": 3.0, "trail": True, "name": "WIDE_3R"},
    {"sl_atr": 2.0, "tp_ratio": 4.0, "trail": True, "name": "WIDE_4R"},
    {"sl_atr": 2.0, "tp_ratio": 5.0, "trail": True, "name": "WIDE_5R"}, # Baseline
    {"sl_atr": 2.5, "tp_ratio": 3.0, "trail": True, "name": "XWIDE_3R"},
]

def load_backtest_data():
    df5 = pd.read_csv(DATA_FILE)
    df5.index = pd.to_datetime(df5['Datetime'])
    df5.index.name = 'index_datetime'
    df5.columns = [c.lower() for c in df5.columns]
    
    df1j = pd.read_csv(DATA_JAN_1M)
    df1j.index = pd.to_datetime(df1j['Timestamp'])
    df1j.index.name = 'index_datetime'
    df1j.columns = [c.lower() for c in df1j.columns]
    
    df5j = df1j.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    df = pd.concat([df5j, df5], sort=False)
    df = df.sort_index()
    df = df[df.index.month.isin([1, 2, 4, 5])]
    return df

def simulate_trade(df, entry_idx, direction, tp_sl_config):
    entry_bar = df.iloc[entry_idx]
    entry_price = entry_bar['close']
    
    if entry_idx < 14: return None
    atr = (df['high'] - df['low']).iloc[entry_idx-14:entry_idx].mean()
    if atr == 0: return None

    sl_dist = atr * tp_sl_config['sl_atr']
    risk_amt = CAPITAL * RISK_PCT
    position_size = risk_amt / sl_dist if sl_dist > 0 else 0
    
    if direction == 'BULLISH':
        sl_price = entry_price - sl_dist
        tp_price = entry_price + (sl_dist * tp_sl_config['tp_ratio'])
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - (sl_dist * tp_sl_config['tp_ratio'])
        
    exit_price = entry_price
    exit_time = None
    result = "LOSS"
    
    trailing_sl = sl_price
    for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
        current_bar = df.iloc[j]
        if tp_sl_config.get('trail', False):
            if direction == 'BULLISH':
                new_trail = current_bar['close'] - (atr * tp_sl_config['sl_atr'])
                trailing_sl = max(trailing_sl, new_trail)
            else:
                new_trail = current_bar['close'] + (atr * tp_sl_config['sl_atr'])
                trailing_sl = min(trailing_sl, new_trail)
        
        active_sl = trailing_sl
        if direction == 'BULLISH':
            if current_bar['low'] <= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                result = "WIN" if exit_price > entry_price else "LOSS"
                break
            if current_bar['high'] >= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                break
        else:
            if current_bar['high'] >= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                result = "WIN" if exit_price < entry_price else "LOSS"
                break
            if current_bar['low'] <= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                break
                    
    if exit_time is None:
        eod_idx = min(entry_idx + 100, len(df) - 1)
        exit_price = df.iloc[eod_idx]['close']
        exit_time = df.index[eod_idx]
        result = "EOD"
        
    pnl = (exit_price - entry_price) * position_size if direction == 'BULLISH' else (entry_price - exit_price) * position_size
    return {"pnl": pnl, "result": result}

def run_backtest_with_config(engine, df, signals_cache, config):
    trades = []
    for i, signals in signals_cache.items():
        best_sig = max(signals, key=lambda x: x.confidence)
        direction = 'BULLISH' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
        res = simulate_trade(df, i, direction, config)
        if res:
            trades.append(res)
    
    if not trades:
        return {"trades": 0, "win_rate": 0, "pf": 0, "pnl": 0}
    
    df_res = pd.DataFrame(trades)
    wins = df_res[df_res['result'] == 'WIN']
    losses = df_res[df_res['result'] == 'LOSS']
    pnl = df_res['pnl'].sum()
    win_rate = len(wins) / len(df_res) * 100
    pf = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 else float('inf')
    
    return {"trades": len(df_res), "win_rate": win_rate, "pf": pf, "pnl": pnl}

def main():
    engine = UnifiedStrategyEngine()
    df = load_backtest_data()
    
    print("Pre-calculating signals...")
    signals_cache = {}
    BLACKLISTED = {'Market Structure', 'Supply & Demand', 'Order Blocks', 'Descending Channel', 'Triple Bottom', 'Inverse Head and Shoulders', 'Ascending Channel', 'Bullish Engulfing', 'Morning Star', 'Fair Value Gaps (FVG)', 'Resistance', 'Bear Flag', 'Ascending Triangle'}

    for i in range(50, len(df), 3):
        current_bar = df.iloc[i]
        if current_bar.name.weekday() in [0, 1]: continue
        
        # Step 1 window: 9:50 to 12:30
        time_min = current_bar.name.hour * 60 + current_bar.name.minute
        if time_min < 590 or time_min > 750: continue
        
        current_window = df.iloc[:i+1]
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals: continue
        
        signals = [s for s in signals if s.strategy_name not in BLACKLISTED]
        if not signals: continue
        
        best_sig = max(signals, key=lambda x: x.confidence)
        if best_sig.confidence < 0.85: continue # Reverted Step 2 floor to 0.85
        
        signals_cache[i] = signals

    print(f"Signals found at {len(signals_cache)} points. Running sweep...")
    print(f"{'Config':>12} | Trades | WR% | PF | P&L")
    print("-" * 50)
    
    for config in ATR_CONFIGS:
        res = run_backtest_with_config(engine, df, signals_cache, config)
        print(f"{config['name']:>12} | {res['trades']:>6} | {res['win_rate']:>4.1f} | {res['pf']:.2f} | ₹{res['pnl']:,.0f}")

if __name__ == "__main__":
    main()
