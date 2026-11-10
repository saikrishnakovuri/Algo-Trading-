import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter
from modules.regime_gate import RegimeGate
from modules.vix_filter import VIXDirectionalFilter

MAX_WORKERS = 8
MIDCAP_DATA_DIR = "data/nifty200"

# Target Midcaps found by find_tradeable_midcaps.py
MIDCAP_SYMBOLS = ['ATGL', 'ADANIENSOL', 'TATAINVEST', 'ADANIPOWER', 'ASTRAL', 'SUZLON', 'BHEL', 'RADICO', 'BLUESTARCO', 'ADANIGREEN', 'LODHA', 'COCHINSHIP', 'SIEMENS', 'ADANIENT', 'KALYANKJIL', 'VOLTAS', 'HDFCAMC', 'SAIL', 'BSE', 'JSWENERGY', 'JUBLFOOD', 'RVNL', 'INDIANB', 'MCX', '360ONE', 'COFORGE', 'PRESTIGE', 'NATIONALUM', 'MOTHERSON', 'VBL']

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
            'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION', 'SWEEP_RETEST', 'STRUCTURE']},
            'regime': regime
        }
    return regime_map

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    data_path = os.path.join(MIDCAP_DATA_DIR, f"{symbol}_1m.csv")
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    # Midcap data uses 'Datetime'
    df_raw['Datetime'] = pd.to_datetime(df_raw['Datetime'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Datetime', inplace=True)
    df_raw.sort_index(inplace=True)
    
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    # Initialize Engines
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine()
    sweep_engine = SweepRetestEngine()
    struct_engine = StructureStrategyEngine()
    
    # Pre-calculate indicators
    df_mr = mr_engine._compute_indicators(df_5m)
    consolidations = mom_engine.detect_consolidation(df_5m)
    
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    signals = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_dt).tz_localize('Asia/Kolkata')
    
    for i in range(50, len(df_5m) - 13):
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

        # --- 1. LIQUIDITY_TRAP (REVERSE MOMENTUM) ---
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], conf)
            if allowed and adj_conf >= min_conf:
                # Normal Momentum (for comparison)
                signals.append({'engine': 'MOMENTUM', 'dir': mom_sig['direction'], 'entry': df_5m.iloc[i]['Close'], 'idx': i})
                # Liquidity Trap (Reversed)
                rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
                signals.append({'engine': 'LIQUIDITY_TRAP', 'dir': rev_dir, 'entry': df_5m.iloc[i]['Close'], 'idx': i})

        # --- 2. CONFIRMED_MR ---
        row = df_mr.iloc[i]
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': 0.5}
        trend_ok, _ = mr_engine._check_anti_trend_filter(row)
        if trend_ok:
            bb = mr_engine._check_bb_reversion(row, settings)
            vwap = mr_engine._check_vwap_reversion(row, settings)
            rsi = mr_engine._check_rsi_extreme(row, settings)
            fired = [s for s in [bb, vwap, rsi] if s is not None]
            if fired:
                direction = 'LONG' if sum(1 for s in fired if s['direction'] == 'LONG') > sum(1 for s in fired if s['direction'] == 'SHORT') else 'SHORT'
                if r_info['allowed']['MEAN_REVERSION']:
                    total_score = sum(s['score'] for s in [s for s in fired if s['direction'] == direction]) + mr_engine._compute_bonuses(row, df_mr, i)[0]
                    conf = min(100, int(total_score * 10))
                    vix_dir = 'CE' if direction == 'LONG' else 'PE'
                    adj_conf, allowed, _ = vix_filter.filter_signal(vix_dir, conf)
                    if allowed and adj_conf >= min_conf:
                        # Normal MR (for comparison)
                        signals.append({'engine': 'MEAN_REVERSION', 'dir': vix_dir, 'entry': row['close'], 'idx': i})
                        # Confirmed MR
                        next_bar = df_5m.iloc[i+1]
                        confirmed = (next_bar['Close'] > df_5m.iloc[i]['Close']) if vix_dir == 'CE' else (next_bar['Close'] < df_5m.iloc[i]['Close'])
                        if confirmed:
                            signals.append({'engine': 'CONFIRMED_MR', 'dir': vix_dir, 'entry': next_bar['Close'], 'idx': i+1})

    audit_results = []
    for s in signals:
        idx = s['idx']; entry = s['entry']
        lookahead = df_5m.iloc[idx+1 : idx+13]
        if lookahead.empty: continue
        if s['dir'] == 'CE':
            mfe = (lookahead['High'].max() - entry) / entry * 100
            mae = (entry - lookahead['Low'].min()) / entry * 100
        else:
            mfe = (entry - lookahead['Low'].min()) / entry * 100
            mae = (lookahead['High'].max() - entry) / entry * 100
        audit_results.append({'engine': s['engine'], 'mfe': mfe, 'mae': mae, 'correct': mfe > 0.3})
    return audit_results

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    # Test Period: April 8-20, 2026 (based on available data in nifty200)
    start_test = datetime(2026, 4, 8); end_test = datetime(2026, 4, 20)
    regime_test = get_regime_series(start_test, end_test)
    
    print(f"Running Mid-cap Signal Audit (April 8-20) for {len(MIDCAP_SYMBOLS)} stocks...")
    args = [(s, start_test, end_test, regime_test, vix_df) for s in MIDCAP_SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex: results = list(ex.map(process_symbol, args))
    all_res = [r for res in results for r in res]
    
    if not all_res:
        print("No signals generated."); return

    df = pd.DataFrame(all_res)
    print("\nA. MID-CAP SIGNAL QUALITY TABLE (Accuracy, MFE, MAE)")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    print("| Engine | Signals | Accuracy | Avg MFE | Avg MAE | MFE > MAE % |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    ranking = []
    for eng in ['LIQUIDITY_TRAP', 'CONFIRMED_MR', 'MOMENTUM', 'MEAN_REVERSION']:
        sub = df[df['engine'] == eng]
        if sub.empty: continue
        acc = sub['correct'].sum() / len(sub) * 100
        avg_mfe = sub['mfe'].mean(); avg_mae = sub['mae'].mean()
        mfe_gt_mae = (sub['mfe'] > sub['mae']).sum() / len(sub) * 100
        ranking.append({'name': eng, 'signals': len(sub), 'acc': acc, 'mfe': avg_mfe, 'mae': avg_mae, 'ratio': mfe_gt_mae})

    ranking = sorted(ranking, key=lambda x: x['acc'], reverse=True)
    for r in ranking:
        print(f"| {r['name']} | {r['signals']} | {r['acc']:.1f}% | {r['mfe']:.3f}% | {r['mae']:.3f}% | {r['ratio']:.1f}% |")

if __name__ == "__main__":
    main()
