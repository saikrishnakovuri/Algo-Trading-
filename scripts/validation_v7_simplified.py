import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.regime_gate import RegimeGate
from modules.vix_filter import VIXDirectionalFilter

INITIAL_CAPITAL = 100000.0
MAX_WORKERS = 8
MIDCAP_DATA_DIR = "data/nifty200"
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
            'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION']},
            'regime': regime
        }
    return regime_map

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    data_path = os.path.join(MIDCAP_DATA_DIR, f"{symbol}_1m.csv")
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Datetime'] = pd.to_datetime(df_raw['Datetime'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Datetime', inplace=True)
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
    entry_gate_time = time(13, 30)
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist or ts > end_ist: continue
        if ts <= last_exit_ts: continue
        
        # 1. TIME GATE: No new entries after 13:30 IST
        if ts.time() > entry_gate_time:
            continue

        r_info = regime_map.get(ts)
        if not r_info: continue
        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        is_danger = (vix_filter.vix_direction in ["SPIKE", "RISING"]) or (r_info['regime'] in ["VOLATILE", "CHOPPY"])
        mode_label = "DANGER" if is_danger else "NORMAL"
        min_conf = 80 if is_danger else 70

        row = df_mr.iloc[i]
        # Hourly ATR Proxy for SL
        dist = row['atr'] * 2.5
        best_sig = None
        
        # --- Engine 1: LIQUIDITY_TRAP (REVERSE MOMENTUM) ---
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
            if allowed and adj_conf >= min_conf:
                entry = df_5m.iloc[i]['Close']
                sl = entry - dist if rev_dir == 'CE' else entry + dist
                t1 = entry + 1.5 * dist if rev_dir == 'CE' else entry - 1.5 * dist # NEW T1 = 1.5R
                be_trigger = entry + 0.7 * dist if rev_dir == 'CE' else entry - 0.7 * dist # NEW BE = 0.7R
                best_sig = {'engine': 'LIQUIDITY_TRAP', 'direction': rev_dir, 'entry': entry, 'sl': sl, 't1': t1, 'be_trigger': be_trigger, 'dist': dist, 'conf': adj_conf}

        # --- Engine 2: CONFIRMED_MR ---
        if not best_sig:
            settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': 0.5}
            trend_ok, _ = mr_engine._check_anti_trend_filter(row)
            if trend_ok:
                bb = mr_engine._check_bb_reversion(row, settings); vwap = mr_engine._check_vwap_reversion(row, settings); rsi = mr_engine._check_rsi_extreme(row, settings)
                fired = [s for s in [bb, vwap, rsi] if s is not None]
                if fired:
                    direction = 'LONG' if sum(1 for s in fired if s['direction'] == 'LONG') > sum(1 for s in fired if s['direction'] == 'SHORT') else 'SHORT'
                    vix_dir = 'CE' if direction == 'LONG' else 'PE'
                    total_score = sum(s['score'] for s in [s for s in fired if s['direction'] == direction]) + mr_engine._compute_bonuses(row, df_mr, i)[0]
                    conf = min(100, int(total_score * 10))
                    adj_conf, allowed, _ = vix_filter.filter_signal(vix_dir, conf)
                    if allowed and adj_conf >= min_conf:
                        if i + 1 < len(df_5m):
                            next_bar = df_5m.iloc[i+1]
                            confirmed = (next_bar['Close'] > df_5m.iloc[i]['Close']) if vix_dir == 'CE' else (next_bar['Close'] < df_5m.iloc[i]['Close'])
                            if confirmed:
                                entry = next_bar['Close']
                                sl = entry - dist if vix_dir == 'CE' else entry + dist
                                t1 = entry + 1.5 * dist if vix_dir == 'CE' else entry - 1.5 * dist
                                be_trigger = entry + 0.7 * dist if vix_dir == 'CE' else entry - 0.7 * dist
                                best_sig = {'engine': 'CONFIRMED_MR', 'direction': vix_dir, 'entry': entry, 'sl': sl, 't1': t1, 'be_trigger': be_trigger, 'dist': dist, 'conf': adj_conf}

        if best_sig:
            entry, sl, t1, be_trigger, dist = best_sig['entry'], best_sig['sl'], best_sig['t1'], best_sig['be_trigger'], best_sig['dist']
            orig_sl = sl
            
            exit_p = entry; exit_time = ts; exit_reason = "EOD"
            be_active = False; t1_hit = False; sl_hit = False
            
            start_j = i+1 if best_sig['engine'] == 'LIQUIDITY_TRAP' else i+2
            for j in range(start_j, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                
                # Check BE Trigger first
                if not be_active:
                    if best_sig['direction'] == 'CE':
                        if curr['High'] >= be_trigger: be_active = True; sl = entry
                    else:
                        if curr['Low'] <= be_trigger: be_active = True; sl = entry
                
                if best_sig['direction'] == 'CE':
                    if curr['Low'] <= sl: 
                        sl_hit = True; exit_p = sl; exit_time = df_5m.index[j]
                        exit_reason = "BE" if be_active else "SL"
                        break
                    if curr['High'] >= t1: 
                        t1_hit = True; exit_p = t1; exit_time = df_5m.index[j]
                        exit_reason = "T1"
                        break
                else:
                    if curr['High'] >= sl: 
                        sl_hit = True; exit_p = sl; exit_time = df_5m.index[j]
                        exit_reason = "BE" if be_active else "SL"
                        break
                    if curr['Low'] <= t1: 
                        t1_hit = True; exit_p = t1; exit_time = df_5m.index[j]
                        exit_reason = "T1"
                        break
            
            if not sl_hit and not t1_hit:
                k = i
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date(): k += 1
                exit_p = df_5m.iloc[k]['Close']; exit_time = df_5m.index[k]
                exit_reason = "EOD"

            last_exit_ts = exit_time
            # Net R: T1=1.5, SL=-1.0, BE=0, EOD=variable
            r_mult = (exit_p - entry)/dist if best_sig['direction'] == 'CE' else (entry - exit_p)/dist
            trades.append({'ts': ts, 'symbol': symbol, 'r': r_mult, 'mode': mode_label, 'entry': entry, 'exit_p': exit_p, 'dist': dist, 'reason': exit_reason})
            
    return trades

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    start_test = datetime(2026, 4, 8); end_test = datetime(2026, 4, 20)
    regime_test = get_regime_series(start_test, end_test)
    
    print(f"Running V7 SIMPLIFIED EXECUTION for {len(MIDCAP_SYMBOLS)} stocks...")
    args = [(s, start_test, end_test, regime_test, vix_df) for s in MIDCAP_SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex: results = list(ex.map(process_symbol, args))
    all_t = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    equity = INITIAL_CAPITAL
    mode_stats = {"NORMAL": {"trades": 0, "gross": 0.0, "costs": 0.0}, "DANGER": {"trades": 0, "gross": 0.0, "costs": 0.0}}
    exit_counts = {"T1": 0, "SL": 0, "BE": 0, "EOD": 0}
    total_costs = 0
    
    for t in all_t:
        risk_pct = 0.005 if t['mode'] == "DANGER" else 0.01
        risk_amt = equity * risk_pct
        qty = risk_amt / t['dist']
        if (qty * t['entry']) > (equity * 5.0): qty = (equity * 5.0) / t['entry']
        if qty < 1: continue
        
        # Brokerage Logic
        buy_t = qty * t['entry']; sell_t = qty * t['exit_p']
        costs = 40 + (sell_t * 0.00025) + ((buy_t + sell_t) * 0.0000345) + 7.2 + (buy_t * 0.00003) + ((buy_t + sell_t) * 0.000001)
        gross = t['r'] * (qty * t['dist'])
        net = gross - costs
        equity += net
        total_costs += costs
        
        mode_stats[t['mode']]['trades'] += 1
        mode_stats[t['mode']]['gross'] += gross
        mode_stats[t['mode']]['costs'] += costs
        exit_counts[t['reason']] = exit_counts.get(t['reason'], 0) + 1

    print("\nB. FULL EXECUTION BACKTEST (NET P&L)")
    print(f"Final Capital: INR {equity:,.2f}")
    print(f"Total Return: {((equity/INITIAL_CAPITAL)-1)*100:.2f}%")
    print(f"Avg Cost per Trade: INR {total_costs/max(1, len(all_t)):.2f}")

    print("\nMODE SPLIT TABLE:")
    print(f"{'Mode':<10} | {'Trades':<8} | {'Gross PnL':<12} | {'Costs':<10} | {'Net PnL':<12}")
    print("-" * 60)
    for m in ["NORMAL", "DANGER"]:
        s = mode_stats[m]
        print(f"{m:<10} | {s['trades']:<8} | {s['gross']:>12,.2f} | {s['costs']:>10,.2f} | {(s['gross']-s['costs']):>12,.2f}")

    print("\nC. EXIT BREAKDOWN TABLE:")
    print(f"{'Exit Type':<15} | {'Count':<8} | {'% of Total':<12}")
    print("-" * 40)
    total = sum(exit_counts.values())
    for k, v in exit_counts.items():
        print(f"{k:<15} | {v:<8} | {(v/max(1,total))*100:>10.1f}%")

if __name__ == "__main__":
    main()
