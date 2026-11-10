
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# --- CONFIG ---
DATA_FILE_5M = "../data/nifty50_5m.csv"
DATA_FILE_JAN_1M = "../data/nifty_index/NIFTY_Jan2026.csv"

PHASE1_CONFIG = {
    'phase': 1,
    'capital': 500000,
    'risk_pct': 0.01,
    'scan_interval': 1,
    'lookahead_bars': 200,
    'output_csv': 'pipeline/results/phase1_raw_results.csv',
    'tp_sl_configs': [
        {'name': 'TRAIL_2ATR_NOTP', 'sl_atr': 2.0, 'tp_ratio': None, 'trail': True},
        {'name': 'TRAIL_1.5ATR_NOTP', 'sl_atr': 1.5, 'tp_ratio': None, 'trail': True},
        {'name': 'TRAIL_2.5ATR_NOTP', 'sl_atr': 2.5, 'tp_ratio': None, 'trail': True},
        {'name': 'FIXED_2R', 'sl_atr': 1.5, 'tp_ratio': 2.0, 'trail': False},
        {'name': 'FIXED_3R', 'sl_atr': 1.5, 'tp_ratio': 3.0, 'trail': False},
        {'name': 'FIXED_5R', 'sl_atr': 2.0, 'tp_ratio': 5.0, 'trail': False},
    ],
}

def load_all_data():
    print("Loading and combining data...")
    # Feb-May 5m
    df5 = pd.read_csv(DATA_FILE_5M)
    df5.index = pd.to_datetime(df5['Datetime'])
    df5.columns = [c.lower() for c in df5.columns]
    
    # Jan 1m
    df1j = pd.read_csv(DATA_FILE_JAN_1M)
    df1j.index = pd.to_datetime(df1j['Timestamp'])
    df1j.columns = [c.lower() for c in df1j.columns]
    
    df5j = df1j.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    df = pd.concat([df5j, df5], sort=False)
    df = df.sort_index()
    # Filter for Jan-May 2026
    df = df[df.index.year == 2026]
    return df

def detect_regime(df, lookback=50):
    if len(df) < lookback: return 'UNKNOWN'
    recent = df.iloc[-lookback:]
    ma20 = recent['close'].rolling(20).mean()
    if len(ma20.dropna()) < 10: return 'UNKNOWN'
    slope = (ma20.iloc[-1] - ma20.iloc[-10]) / ma20.iloc[-10] * 100
    if slope > 0.15: return 'TRENDING_UP'
    elif slope < -0.15: return 'TRENDING_DOWN'
    else: return 'RANGING'

def simulate_trade(df, entry_idx, direction, tp_sl_config, lookahead=200):
    entry_bar = df.iloc[entry_idx]
    entry_price = entry_bar['close']
    if entry_idx < 14: return None
    
    # ATR for SL
    sub_df = df.iloc[entry_idx-14:entry_idx]
    tr = pd.concat([
        sub_df['high'] - sub_df['low'],
        (sub_df['high'] - sub_df['close'].shift(1)).abs(),
        (sub_df['low'] - sub_df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.mean()
    if atr == 0: return None
    
    sl_dist = atr * tp_sl_config['sl_atr']
    risk_amt = 500000 * 0.01
    position_size = risk_amt / sl_dist if sl_dist > 0 else 0
    
    tp_price = None
    if tp_sl_config.get('tp_ratio'):
        tp_price = entry_price + (sl_dist * tp_sl_config['tp_ratio']) if direction == 'BULLISH' else entry_price - (sl_dist * tp_sl_config['tp_ratio'])
    
    trailing_sl = entry_price - sl_dist if direction == 'BULLISH' else entry_price + sl_dist
    exit_price = entry_price
    exit_time = None
    result = "LOSS"
    exit_reason = "UNKNOWN"
    is_trailing = tp_sl_config.get('trail', False)
    
    for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(df))):
        bar = df.iloc[j]
        if is_trailing:
            if direction == 'BULLISH':
                new_trail = bar['close'] - (atr * tp_sl_config['sl_atr'])
                trailing_sl = max(trailing_sl, new_trail)
            else:
                new_trail = bar['close'] + (atr * tp_sl_config['sl_atr'])
                trailing_sl = min(trailing_sl, new_trail)
        
        active_sl = trailing_sl
        if direction == 'BULLISH':
            if bar['low'] <= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                exit_reason = 'TRAIL_HIT' if is_trailing and active_sl > (entry_price - sl_dist) else 'SL_HIT'
                result = "WIN" if exit_price > entry_price else "LOSS"
                break
            if tp_price and bar['high'] >= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                exit_reason = 'TP_HIT'
                break
        else:
            if bar['high'] >= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                exit_reason = 'TRAIL_HIT' if is_trailing and active_sl < (entry_price + sl_dist) else 'SL_HIT'
                result = "WIN" if exit_price < entry_price else "LOSS"
                break
            if tp_price and bar['low'] <= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = "WIN"
                exit_reason = 'TP_HIT'
                break
    
    if exit_time is None:
        eod_idx = min(entry_idx + lookahead, len(df) - 1)
        exit_price = df.iloc[eod_idx]['close']
        exit_time = df.index[eod_idx]
        result = "EOD"
        exit_reason = "EOD"
    
    price_change = (exit_price - entry_price) if direction == 'BULLISH' else (entry_price - exit_price)
    pnl = price_change * position_size
    duration = (exit_time - df.index[entry_idx]).total_seconds() / 60
    rr_achieved = price_change / sl_dist if sl_dist > 0 else 0
    
    return {
        'entry_time': df.index[entry_idx],
        'exit_time': exit_time,
        'entry_price': round(entry_price, 2),
        'exit_price': round(exit_price, 2),
        'pnl': round(pnl, 2),
        'result': result,
        'exit_reason': exit_reason,
        'holding_period_minutes': round(duration, 0),
        'risk_reward_achieved': round(rr_achieved, 2),
    }

def run_raw_discovery(config):
    engine = UnifiedStrategyEngine()
    df = load_all_data()
    all_trades = []
    trade_id = 0
    
    print(f"Scanning {len(df)} bars...")
    for i in range(50, len(df), config['scan_interval']):
        if i % 500 == 0: print(f"  Progress: {i}/{len(df)}...")
        
        current_bar = df.iloc[i]
        current_window = df.iloc[:i+1]
        
        # Get ALL signals (pass backtest_mode=True to engine)
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals: continue
        
        regime = detect_regime(current_window)
        
        for sig in signals:
            if sig.confidence <= 0: continue
            direction = 'BULLISH' if sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
            
            for tpsl in config['tp_sl_configs']:
                trade_id += 1
                result = simulate_trade(df, i, direction, tpsl, config['lookahead_bars'])
                if not result: continue
                
                result.update({
                    'trade_id': trade_id,
                    'strategy_name': sig.strategy_name,
                    'confidence': sig.confidence,
                    'direction': 'CE' if direction == 'BULLISH' else 'PE',
                    'sl_method': tpsl['name'],
                    'day_of_week': current_bar.name.strftime('%A'),
                    'hour_of_entry': current_bar.name.hour,
                    'market_regime': regime,
                    'month': current_bar.name.strftime('%B')
                })
                all_trades.append(result)
    
    results_df = pd.DataFrame(all_trades)
    results_df.to_csv(config['output_csv'], index=False)
    return results_df

if __name__ == "__main__":
    results = run_raw_discovery(PHASE1_CONFIG)
    print(f"\nPhase 1 complete: {len(results)} trades saved.")
    print(f"Net P&L: ₹{results['pnl'].sum():,.2f}")
    print(f"Win Rate: {(results['result']=='WIN').mean()*100:.1f}%")
