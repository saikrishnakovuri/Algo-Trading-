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

def calc_options_costs(qty, entry_p, exit_p):
    brokerage = 40.0
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    return brokerage + stt + exchange + 10.0

def process_symbol_sweep(args):
    symbol, start_dt, end_dt, vix_df = args
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
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_dt).tz_localize('Asia/Kolkata')
    entry_gate_time = time(13, 30)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist or ts > end_ist: continue
        if ts.time() > entry_gate_time: continue

        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
            
            if allowed:
                entry_spot = df_5m.iloc[i]['Close']
                atr = df_5m.iloc[i]['atr']
                sl_dist = atr * 2.5 
                
                vix = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
                entry_p = entry_spot * 0.006 * (vix/15.0)
                
                lots = max(1, int(RISK_PER_TRADE_INR / (entry_p * LOT_SIZE)))
                lots = min(lots, MAX_LOTS)
                qty = lots * LOT_SIZE
                
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
                
                costs = calc_options_costs(qty, entry_p, exit_p)
                net_pnl = ((exit_p - entry_p) * qty) - costs
                
                trades.append({'ts': ts, 'conf': adj_conf, 'net': net_pnl, 'gross': net_pnl + costs, 'costs': costs, 'reason': exit_reason, 'entry_p': entry_p, 'qty': qty})
                
    return trades

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    start_d = datetime(2026, 4, 8); end_d = datetime(2026, 4, 20)
    
    print(f"Running Confidence Sweep for {len(MIDCAP_SYMBOLS)} stocks...")
    args = [(s, start_d, end_d, vix_df) for s in MIDCAP_SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        results = list(ex.map(process_symbol_sweep, args))
    
    all_t = [t for res in results for t in res]
    
    print("\n| Confidence Threshold | Trades | Win Rate | Gross P&L | Costs | Net P&L | Net/Trade |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for thresh in [65, 70, 75, 80, 85]:
        filtered = [t for t in all_t if t['conf'] >= thresh]
        if not filtered: continue
        
        # Enforce chronological position lock for each threshold for true net
        filtered = sorted(filtered, key=lambda x: x['ts'])
        locked_trades = []
        last_exit = datetime(2000, 1, 1).replace(tzinfo=vix_df.index.tz)
        
        for t in filtered:
            if t['ts'] < last_exit: continue
            locked_trades.append(t)
            last_exit = t['ts'] + timedelta(minutes=90) # Max hold
            
        total_net = sum(t['net'] for t in locked_trades)
        total_gross = sum(t['gross'] for t in locked_trades)
        total_costs = sum(t['costs'] for t in locked_trades)
        wr = sum(1 for t in locked_trades if t['net'] > 0) / len(locked_trades) * 100
        
        print(f"| {thresh}% | {len(locked_trades)} | {wr:.1f}% | {total_gross:>10,.2f} | {total_costs:>10,.2f} | {total_net:>10,.2f} | {total_net/len(locked_trades):.2f} |")

if __name__ == "__main__":
    main()
