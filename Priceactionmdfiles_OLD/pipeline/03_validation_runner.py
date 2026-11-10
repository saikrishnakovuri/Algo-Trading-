
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import json
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

# --- DATA PERIODS FOR VALIDATION ---
# Based on 2026 data availability (Jan-May)
PHASE_PERIODS = {
    2: {'start': '2026-01-01', 'end': '2026-01-31'},
    3: {'start': '2026-02-01', 'end': '2026-02-28'},
    4: {'start': '2026-04-01', 'end': '2026-04-30'},
    5: {'start': '2026-05-01', 'end': '2026-05-31'},
    # Phase 6 will be a re-run of the strongest month for final confirmation
    6: {'start': '2026-01-01', 'end': '2026-05-31'}, 
}

DATA_FILE_5M = "../data/nifty50_5m.csv"
DATA_FILE_JAN_1M = "../data/nifty_index/NIFTY_Jan2026.csv"
CAPITAL = 500000

def load_config():
    with open('pipeline/results/optimized_config.json', 'r') as f:
        return json.load(f)

def save_config(config):
    phase = config['phase']
    backup_path = f'pipeline/results/config_phase{phase-1}_backup.json'
    if os.path.exists('pipeline/results/optimized_config.json'):
        os.rename('pipeline/results/optimized_config.json', backup_path)
    with open('pipeline/results/optimized_config.json', 'w') as f:
        json.dump(config, f, indent=2, default=str)

def load_data_for_period(period):
    print(f"Loading data for {period['start']} to {period['end']}...")
    df5 = pd.read_csv(DATA_FILE_5M)
    df5.index = pd.to_datetime(df5['Datetime'])
    df5.columns = [c.lower() for c in df5.columns]
    
    df1j = pd.read_csv(DATA_FILE_JAN_1M)
    df1j.index = pd.to_datetime(df1j['Timestamp'])
    df1j.columns = [c.lower() for c in df1j.columns]
    df5j = df1j.resample('5min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    
    df = pd.concat([df5j, df5], sort=False)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='first')]
    
    start, end = pd.Timestamp(period['start']), pd.Timestamp(period['end'])
    
    # Ensure start/end match index timezone awareness
    if df.index.tz is not None:
        if start.tz is None: start = start.tz_localize('UTC').tz_convert(df.index.tz)
        if end.tz is None: end = end.tz_localize('UTC').tz_convert(df.index.tz)
    else:
        if start.tz is not None: start = start.tz_localize(None)
        if end.tz is not None: end = end.tz_localize(None)

    mask = (df.index >= start) & (df.index <= end)
    return df.loc[mask]

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
    entry_price = df.iloc[entry_idx]['close']
    if entry_idx < 14: return None
    sub_df = df.iloc[entry_idx-14:entry_idx]
    tr = pd.concat([sub_df['high']-sub_df['low'], (sub_df['high']-sub_df['close'].shift(1)).abs(), (sub_df['low']-sub_df['close'].shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.mean()
    if atr == 0: return None
    
    sl_dist = atr * tp_sl_config['sl_atr']
    position_size = (CAPITAL * 0.01) / sl_dist if sl_dist > 0 else 0
    tp_price = None
    if tp_sl_config.get('tp_ratio'):
        tp_price = entry_price + (sl_dist * tp_sl_config['tp_ratio']) if direction == 'BULLISH' else entry_price - (sl_dist * tp_sl_config['tp_ratio'])
    
    trailing_sl = entry_price - sl_dist if direction == 'BULLISH' else entry_price + sl_dist
    exit_price, exit_time, result = entry_price, None, "LOSS"
    is_trailing = tp_sl_config.get('trail', False)
    
    for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(df))):
        bar = df.iloc[j]
        if is_trailing:
            if direction == 'BULLISH': trailing_sl = max(trailing_sl, bar['close'] - sl_dist)
            else: trailing_sl = min(trailing_sl, bar['close'] + sl_dist)
        
        active_sl = trailing_sl
        if direction == 'BULLISH':
            if bar['low'] <= active_sl: exit_price, exit_time, result = active_sl, df.index[j], ("WIN" if active_sl > entry_price else "LOSS"); break
            if tp_price and bar['high'] >= tp_price: exit_price, exit_time, result = tp_price, df.index[j], "WIN"; break
        else:
            if bar['high'] >= active_sl: exit_price, exit_time, result = active_sl, df.index[j], ("WIN" if active_sl < entry_price else "LOSS"); break
            if tp_price and bar['low'] <= tp_price: exit_price, exit_time, result = tp_price, df.index[j], "WIN"; break
    
    if exit_time is None:
        idx = min(entry_idx + lookahead, len(df) - 1)
        exit_price, exit_time, result = df.iloc[idx]['close'], df.index[idx], "EOD"
    
    pnl = (exit_price - entry_price) * position_size if direction == 'BULLISH' else (entry_price - exit_price) * position_size
    return {'entry_time': df.index[entry_idx], 'exit_time': exit_time, 'entry_price': round(entry_price, 2), 'exit_price': round(exit_price, 2), 'pnl': round(pnl, 2), 'result': result}

def run_validation(config):
    phase = config['phase']
    period = PHASE_PERIODS[phase]
    print(f"\nRUNNING PHASE {phase} VALIDATION: {period['start']} to {period['end']}")
    
    df = load_data_for_period(period)
    if df.empty: return None
    
    engine = UnifiedStrategyEngine()
    SL_CONFIGS = {
        'TRAIL_2ATR_NOTP': {'sl_atr': 2.0, 'tp_ratio': None, 'trail': True},
        'TRAIL_1.5ATR_NOTP': {'sl_atr': 1.5, 'tp_ratio': None, 'trail': True},
        'TRAIL_2.5ATR_NOTP': {'sl_atr': 2.5, 'tp_ratio': None, 'trail': True},
        'FIXED_2R': {'sl_atr': 1.5, 'tp_ratio': 2.0, 'trail': False},
        'FIXED_3R': {'sl_atr': 1.5, 'tp_ratio': 3.0, 'trail': False},
        'FIXED_5R': {'sl_atr': 2.0, 'tp_ratio': 5.0, 'trail': False},
    }
    tpsl = SL_CONFIGS.get(config['sl_method'], SL_CONFIGS['TRAIL_2ATR_NOTP'])
    tpsl['name'] = config['sl_method']
    
    trades = []
    allowed_days, allowed_hours, allowed_strategies = set(config['allowed_days']), set(config['allowed_hours']), set(config['strategies'])
    
    for i in range(50, len(df)):
        bar = df.iloc[i]
        if bar.name.strftime('%A') not in allowed_days or bar.name.hour not in allowed_hours: continue
        
        current_window = df.iloc[:i+1]
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals: continue
        
        for sig in signals:
            if sig.strategy_name not in allowed_strategies: continue
            strat_cfg = config.get('strategy_configs', {}).get(sig.strategy_name, {})
            if sig.confidence < strat_cfg.get('optimal_confidence', 0.80): continue
            
            direction = 'BULLISH' if sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
            if strat_cfg.get('preferred_direction') and ('CE' if direction == 'BULLISH' else 'PE') != strat_cfg['preferred_direction']: continue
            
            regime = detect_regime(current_window)
            if strat_cfg.get('allowed_regimes') and regime not in strat_cfg['allowed_regimes']: continue
            
            res = simulate_trade(df, i, direction, tpsl)
            if res:
                res.update({'strategy_name': sig.strategy_name, 'confidence': sig.confidence, 'day_of_week': bar.name.strftime('%A'), 'hour_of_entry': bar.name.hour, 'market_regime': regime})
                trades.append(res)
    
    res_df = pd.DataFrame(trades)
    res_df.to_csv(f'pipeline/results/phase{phase}_results.csv', index=False)
    return res_df

def analyze_and_update(results_df, config):
    phase = config['phase']
    if results_df is None or results_df.empty:
        print("No trades found. Advancing phase."); config['phase'] += 1; save_config(config); return
    
    pnl = results_df['pnl'].sum()
    print(f"PHASE {phase} P&L: ₹{pnl:,.2f} | Trades: {len(results_df)}")
    
    survivors = []
    for strat, group in results_df.groupby('strategy_name'):
        if group['pnl'].sum() > 0: survivors.append(strat)
    
    if survivors: config['strategies'] = survivors
    config['phase'] += 1
    save_config(config)
    print(f"Survivors: {survivors}. Config updated for Phase {config['phase']}.")

if __name__ == "__main__":
    config = load_config()
    if config['phase'] <= 6:
        results = run_validation(config)
        analyze_and_update(results, config)
    else:
        print("All phases complete.")
