import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine
from modules.vix_filter import VIXDirectionalFilter

INITIAL_CAPITAL = 1000000.0
MAX_WORKERS = 8
LOT_SIZE = 65 
MAX_LOTS = 5
RISK_PER_TRADE_INR = 20000.0 
MIDCAP_DATA_DIR = "data/nifty200"
MIDCAP_SYMBOLS = ['ATGL', 'ADANIENSOL', 'TATAINVEST', 'ADANIPOWER', 'ASTRAL', 'SUZLON', 'BHEL', 'RADICO', 'BLUESTARCO', 'ADANIGREEN', 'LODHA', 'COCHINSHIP', 'SIEMENS', 'ADANIENT', 'KALYANKJIL', 'VOLTAS', 'HDFCAMC', 'SAIL', 'BSE', 'JSWENERGY', 'JUBLFOOD', 'RVNL', 'INDIANB', 'MCX', '360ONE', 'COFORGE', 'PRESTIGE', 'NATIONALUM', 'MOTHERSON', 'VBL']

MAX_DAILY_TRADES = 5
MAX_SIMULTANEOUS = 2

def calc_options_costs(qty, entry_p, exit_p):
    brokerage = 40.0
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    return brokerage + stt + exchange + 10.0

def process_symbol_sweep(args):
    symbol, clusters, vix_df = args
    data_path = os.path.join(MIDCAP_DATA_DIR, f"{symbol}_1m.csv")
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Datetime'] = pd.to_datetime(df_raw['Datetime'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Datetime', inplace=True)
    df_raw.sort_index(inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    ie = IndicatorEngine()
    df_5m['atr'] = ie.calculate_atr(df_5m)
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    trades = []
    entry_gate_time = time(13, 30)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        in_cluster = any(start <= ts.date() <= end for start, end in clusters)
        if not in_cluster: continue
        if ts.time() > entry_gate_time: continue

        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
            
            if allowed:
                entry_spot = df_5m.iloc[i]['Close']
                vix = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
                entry_p = entry_spot * 0.006 * (vix/15.0)
                
                target_p = entry_p * 1.5
                be_trigger_p = entry_p * 1.35 
                sl_p = entry_p * 0.7
                
                exit_p = entry_p; exit_reason = "EOD"
                be_active = False
                for j in range(i+1, min(i+20, len(df_5m))):
                    curr_bar = df_5m.iloc[j]
                    spot_move = (curr_bar['Close'] - entry_spot) / entry_spot
                    if rev_dir == 'PE': spot_move *= -1.0
                    curr_p = entry_p + (0.5 * spot_move * entry_spot) + (0.5 * 0.002 * (spot_move * entry_spot)**2) - (0.5 * (j-i)/12)
                    
                    if not be_active and curr_p >= be_trigger_p:
                        be_active = True; sl_p = entry_p
                    
                    if curr_p >= target_p: exit_p = target_p; exit_reason = "TP"; break
                    if curr_p <= sl_p: exit_p = sl_p; exit_reason = "SL"; break
                
                trades.append({'ts': ts, 'symbol': symbol, 'conf': adj_conf, 'entry_p': entry_p, 'exit_p': exit_p, 'exit_ts': df_5m.index[j]})
                
    return trades

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    clusters = [
        (datetime(2025, 12, 1).date(), datetime(2025, 12, 12).date()),
        (datetime(2025, 12, 24).date(), datetime(2026, 1, 7).date()),
        (datetime(2026, 2, 20).date(), datetime(2026, 3, 6).date()),
        (datetime(2026, 4, 8).date(), datetime(2026, 4, 20).date())
    ]
    
    print(f"Running Advanced Portfolio Sweep (Max 5/day, Max 2 simultaneously)...")
    args = [(s, clusters, vix_df) for s in MIDCAP_SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        results = list(ex.map(process_symbol_sweep, args))
    
    all_raw_signals = [s for res in results for s in res]
    
    print("\n| Confidence Threshold | Trades | Win Rate | Gross P&L | Costs | Net P&L | Net/Trade |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for thresh in [65, 70, 75, 80, 85]:
        filtered = sorted([s for s in all_raw_signals if s['conf'] >= thresh], key=lambda x: x['ts'])
        
        equity = INITIAL_CAPITAL
        active_trades = []
        daily_count = {}
        total_gross = 0; total_costs = 0; wins = 0; trades_taken = 0
        
        for s in filtered:
            dt = s['ts'].date()
            if dt not in daily_count: daily_count[dt] = 0
            
            active_trades = [t for t in active_trades if t['exit_ts'] > s['ts']]
            
            if daily_count[dt] >= MAX_DAILY_TRADES: continue
            if len(active_trades) >= MAX_SIMULTANEOUS: continue
            if any(t['symbol'] == s['symbol'] for t in active_trades): continue
            
            # Position Size
            lots = max(1, int(20000.0 / (s['entry_p'] * 65)))
            lots = min(lots, 5)
            qty = lots * 65
            
            costs = calc_options_costs(qty, s['entry_p'], s['exit_p'])
            gross = (s['exit_p'] - s['entry_p']) * qty
            net = gross - costs
            
            equity += net
            total_gross += gross
            total_costs += costs
            trades_taken += 1
            if net > 0: wins += 1
            active_trades.append({'symbol': s['symbol'], 'exit_ts': s['exit_ts']})
            daily_count[dt] += 1
            
        if trades_taken == 0: continue
        print(f"| {thresh}% | {trades_taken} | {(wins/trades_taken)*100:.1f}% | {total_gross:>10,.2f} | {total_costs:>10,.2f} | {(total_gross-total_costs):>10,.2f} | {(total_gross-total_costs)/trades_taken:.2f} |")

if __name__ == "__main__":
    main()
