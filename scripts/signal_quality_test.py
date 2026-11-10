import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.regime_gate import RegimeGate
from modules.vix_filter import VIXDirectionalFilter

INITIAL_CAPITAL = 100000.0
MAX_WORKERS = 8

def get_regime_series(start_date, end_date):
    nifty_path = "data/nifty50_5m.csv"
    df_nifty_raw = pd.read_csv(nifty_path)
    df_nifty_raw['Timestamp'] = pd.to_datetime(df_nifty_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_nifty_raw.set_index('Timestamp', inplace=True)
    df_nifty_raw = df_nifty_raw.between_time('09:15', '15:30')
    
    start_ist = pd.Timestamp(start_date).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_date).tz_localize('Asia/Kolkata')
    df_nifty = df_nifty_raw[(df_nifty_raw.index >= start_ist - timedelta(days=20)) & (df_nifty_raw.index <= end_ist)]
    
    regime_gate = RegimeGate()
    regime_map = {}
    for i in range(100, len(df_nifty)):
        ts = df_nifty.index[i]
        if ts < start_ist: continue
        regime = regime_gate.update_regime(df_nifty.iloc[max(0, i-150):i+1])
        regime_map[ts] = {
            'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION']},
            'regime': regime
        }
    return regime_map

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_raw.sort_index(inplace=True)
    
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    mr_engine = MeanReversionEngine()
    df_mr = mr_engine._compute_indicators(df_5m)
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    signals = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_dt).tz_localize('Asia/Kolkata')
    
    for i in range(50, len(df_5m) - 13): # Leave room for 12-bar lookahead
        ts = df_5m.index[i]
        if ts < start_ist or ts > end_ist: continue

        r_info = regime_map.get(ts)
        if not r_info: continue

        vix_slice = vix_df[vix_df.index <= ts].tail(20)
        vix_filter.update(vix_slice)
        
        vix_state = vix_filter.vix_direction
        regime = r_info['regime']
        is_danger = (vix_state in ["SPIKE", "RISING"]) or (regime in ["VOLATILE", "CHOPPY"])
        min_conf = 80 if is_danger else 70

        row = df_mr.iloc[i]
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': 1.0 if is_danger else 0.5}
        
        trend_ok, _ = mr_engine._check_anti_trend_filter(row)
        best_sig = None
        
        if trend_ok:
            bb = mr_engine._check_bb_reversion(row, settings)
            vwap = mr_engine._check_vwap_reversion(row, settings)
            rsi = mr_engine._check_rsi_extreme(row, settings)
            fired = [s for s in [bb, vwap, rsi] if s is not None]
            if fired:
                direction = 'LONG' if sum(1 for s in fired if s['direction'] == 'LONG') > sum(1 for s in fired if s['direction'] == 'SHORT') else 'SHORT'
                if r_info['allowed']['MEAN_REVERSION']:
                    aligned = [s for s in fired if s['direction'] == direction]
                    total_score = sum(s['score'] for s in aligned) + mr_engine._compute_bonuses(row, df_mr, i)[0]
                    conf = min(100, int(total_score * 10))
                    vix_direction = 'CE' if direction == 'LONG' else 'PE'
                    adj_conf, allowed, _ = vix_filter.filter_signal(vix_direction, conf)
                    if allowed and adj_conf >= min_conf:
                        best_sig = {'engine': 'MEAN_REVERSION', 'direction': vix_direction, 'entry': row['close']}

        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], min(100, int(mom_sig['score'] * 12)))
                if allowed and adj_conf >= min_conf:
                    best_sig = {'engine': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': df_5m.iloc[i]['Close']}

        if best_sig:
            entry = best_sig['entry']
            lookahead_slice = df_5m.iloc[i+1 : i+13]
            
            if best_sig['direction'] == 'CE':
                max_price = lookahead_slice['High'].max()
                min_price = lookahead_slice['Low'].min()
                mfe = (max_price - entry) / entry * 100
                mae = (entry - min_price) / entry * 100
            else:
                max_price = lookahead_slice['Low'].min() # Lower is better for shorts
                min_price = lookahead_slice['High'].max()
                mfe = (entry - max_price) / entry * 100
                mae = (min_price - entry) / entry * 100
                
            signals.append({
                'ts': ts,
                'engine': best_sig['engine'],
                'mfe': mfe,
                'mae': mae,
                'correct': mfe > 0.3
            })
            
    return signals

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    start_dec = datetime(2025, 12, 1); end_dec = datetime(2025, 12, 12)
    regime_dec = get_regime_series(start_dec, end_dec)
    
    nifty_20 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'ITC', 'LT', 'AXISBANK', 'SBIN', 'BHARTIARTL', 'MARUTI', 'BAJFINANCE', 'HCLTECH', 'SUNPHARMA', 'ADANIENT', 'TITAN', 'ULTRACEMCO', 'NTPC', 'JSWSTEEL', 'POWERGRID']
    all_files = [f.split('_')[0] for f in os.listdir('data/angel_historical') if '_1m.csv' in f]
    symbols_30 = nifty_20 + [s for s in all_files if s not in nifty_20][:10]
    
    print(f"Running Signal Quality Test for {len(symbols_30)} stocks...")
    args = [(s, start_dec, end_dec, regime_dec, vix_df) for s in symbols_30]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex: results = list(ex.map(process_symbol, args))
    all_signals = [s for res in results for s in res]
    
    if not all_signals:
        print("No signals generated."); return

    df_res = pd.DataFrame(all_signals)
    
    total = len(df_res)
    correct_pct = df_res['correct'].sum() / total * 100
    avg_mfe = df_res['mfe'].mean()
    avg_mae = df_res['mae'].mean()
    mfe_gt_mae = (df_res['mfe'] > df_res['mae']).sum() / total * 100

    print("\n| Metric | Value |")
    print("| :--- | :--- |")
    print(f"| Total signals generated | {total} |")
    print(f"| Direction correct within 1 hour (>0.3% move) | {correct_pct:.1f}% |")
    print(f"| Avg MFE (favorable move) | {avg_mfe:.3f}% |")
    print(f"| Avg MAE (adverse move) | {avg_mae:.3f}% |")
    print(f"| MFE > MAE ratio | {mfe_gt_mae:.1f}% |")

    print("\n| Engine | Signals | Accuracy | Avg MFE | Avg MAE |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for eng in df_res['engine'].unique():
        sub = df_res[df_res['engine'] == eng]
        acc = sub['correct'].sum() / len(sub) * 100
        print(f"| {eng} | {len(sub)} | {acc:.1f}% | {sub['mfe'].mean():.3f}% | {sub['mae'].mean():.3f}% |")

if __name__ == "__main__":
    main()
