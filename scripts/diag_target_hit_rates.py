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
    
    trades = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_dt).tz_localize('Asia/Kolkata')
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist or ts > end_ist: continue
        if ts <= last_exit_ts: continue

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
                    adj_conf, allowed, _ = vix_filter.filter_signal('CE' if direction == 'LONG' else 'PE', conf)
                    if allowed and adj_conf >= min_conf:
                        sl, t1, _ = mr_engine._calculate_sl_target(row, direction, aligned[0]['signal_type'], settings)
                        dist = abs(row['close'] - sl)
                        if dist > 0 and (abs(t1 - row['close']) / dist) >= 2.0:
                            best_sig = {'strategy': 'MEAN_REVERSION', 'direction': 'CE' if direction == 'LONG' else 'PE', 'entry': row['close'], 'sl': sl, 't1': t1, 'dist': dist}

        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], min(100, int(mom_sig['score'] * 12)))
                if allowed and adj_conf >= min_conf:
                    sl = mom_sig['sl']
                    dist = abs(mom_sig['entry'] - sl)
                    if dist > 0:
                        t1 = mom_sig['entry'] + (2.0 * dist) if mom_sig['direction'] == 'CE' else mom_sig['entry'] - (2.0 * dist)
                        best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': sl, 't1': t1, 'dist': dist}

        if best_sig:
            entry, sl, t1, dist = best_sig['entry'], best_sig['sl'], best_sig['t1'], best_sig['dist']
            t2 = entry + (3.5 * dist) if best_sig['direction'] == 'CE' else entry - (3.5 * dist)
            t3 = entry + (5.0 * dist) if best_sig['direction'] == 'CE' else entry - (5.0 * dist)
            
            exit_reason = "EOD"; exit_p = entry; exit_time = ts
            
            t1_hit = False; t2_hit = False; t3_hit = False; sl_hit = False
            
            for j in range(i+1, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                
                if best_sig['direction'] == 'CE':
                    if curr['Low'] <= sl: sl_hit = True; exit_p = sl; exit_reason = "SL"; exit_time = df_5m.index[j]; break
                    if not t1_hit and curr['High'] >= t1: t1_hit = True
                    if t1_hit and not t2_hit and curr['High'] >= t2: t2_hit = True
                    if t2_hit and not t3_hit and curr['High'] >= t3: t3_hit = True; exit_p = t3; exit_reason = "T3"; exit_time = df_5m.index[j]; break
                else:
                    if curr['High'] <= sl: sl_hit = True; exit_p = sl; exit_reason = "SL"; exit_time = df_5m.index[j]; break
                    if not t1_hit and curr['Low'] <= t1: t1_hit = True
                    if t1_hit and not t2_hit and curr['Low'] <= t2: t2_hit = True
                    if t2_hit and not t3_hit and curr['Low'] <= t3: t3_hit = True; exit_p = t3; exit_reason = "T3"; exit_time = df_5m.index[j]; break
            
            if not sl_hit and not t3_hit:
                # Find EOD Close
                k = i
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date(): k += 1
                exit_p = df_5m.iloc[k]['Close']; exit_time = df_5m.index[k]
                if t2_hit: exit_reason = "T2_EOD"
                elif t1_hit: exit_reason = "T1_EOD"
                else: exit_reason = "EOD"

            last_exit_ts = exit_time
            # P&L Calculation for scaling: 50% at T1, 25% at T2, 25% at T3/EOD
            # This is complex to sum exactly, but we just need hit counts.
            trades.append({'symbol': symbol, 't1': t1_hit, 't2': t2_hit, 't3': t3_hit, 'sl': sl_hit, 'reason': exit_reason, 'entry': entry, 'exit_p': exit_p, 'r': (exit_p - entry)/dist if best_sig['direction'] == 'CE' else (entry - exit_p)/dist})
            
    return trades

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    vix_df.sort_index(inplace=True)
    
    start_dec = datetime(2025, 12, 1); end_dec = datetime(2025, 12, 12)
    regime_dec = get_regime_series(start_dec, end_dec)
    
    nifty_20 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'ITC', 'LT', 'AXISBANK', 'SBIN', 'BHARTIARTL', 'MARUTI', 'BAJFINANCE', 'HCLTECH', 'SUNPHARMA', 'ADANIENT', 'TITAN', 'ULTRACEMCO', 'NTPC', 'JSWSTEEL', 'POWERGRID']
    all_files = [f.split('_')[0] for f in os.listdir('data/angel_historical') if '_1m.csv' in f]
    symbols_30 = nifty_20 + [s for s in all_files if s not in nifty_20][:10]
    
    args = [(s, start_dec, end_dec, regime_dec, vix_df) for s in symbols_30]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex: results = list(ex.map(process_symbol, args))
    all_t = [t for res in results for t in res]
    
    total = len(all_t)
    sl_count = sum(1 for t in all_t if t['sl'])
    t1_count = sum(1 for t in all_t if t['t1'])
    t2_count = sum(1 for t in all_t if t['t2'])
    t3_count = sum(1 for t in all_t if t['t3'])
    eod_only = sum(1 for t in all_t if not t['t1'] and not t['sl'])
    
    print("\n| Exit Type | Count | % of Total | Avg R-Mult |")
    print("| :--- | :--- | :--- | :--- |")
    print(f"| SL Hit | {sl_count} | {(sl_count/total)*100:.1f}% | -1.00 |")
    print(f"| T1 Hit (2R) | {t1_count} | {(t1_count/total)*100:.1f}% | 2.00+ |")
    print(f"| T2 Hit (3.5R) | {t2_count} | {(t2_count/total)*100:.1f}% | 3.50+ |")
    print(f"| T3 Hit (5R) | {t3_count} | {(t3_count/total)*100:.1f}% | 5.00 |")
    print(f"| EOD (No Target) | {eod_only} | {(eod_only/total)*100:.1f}% | {sum(t['r'] for t in all_t if not t['t1'] and not t['sl'])/max(1, eod_only):.2f} |")

if __name__ == "__main__":
    main()
