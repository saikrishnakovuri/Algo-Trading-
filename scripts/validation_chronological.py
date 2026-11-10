import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine
from modules.regime_gate import RegimeGate
from modules.vix_filter import VIXDirectionalFilter
from modules.event_calendar import EventCalendar

INITIAL_CAPITAL = 100000.0
SYMBOLS = ['SBIN', 'TCS', 'TITAN', 'ITC', 'LT', 'M&M', 'ADANIENT', 'BHARTIARTL', 'SUNPHARMA', 'KOTAKBANK']
RISK_PER_TRADE = 1000.0
CONFIDENCE_THRESHOLD = 85
MAX_DAILY_TRADES = 5
MAX_SIMULTANEOUS = 2

def calc_costs(qty, entry, exit_p):
    buy_t = qty * entry; sell_t = qty * exit_p
    costs = 40 + (sell_t * 0.00025) + ((buy_t + sell_t) * 0.0000345) + 7.2 + (buy_t * 0.00003) + ((buy_t + sell_t) * 0.000001)
    return costs

def get_base_data(df, i):
    row = df.iloc[i]
    prev_20 = df.iloc[max(0, i-20):i+1]
    return {
        'price': row['Close'],
        'atr': row.get('atr', (row['High'] - row['Low'])),
        'hi_20': prev_20['High'].max(),
        'lo_20': prev_20['Low'].min(),
    }

def get_all_signals(args):
    symbol, start_d, end_d, regime_map, vix_df = args
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return []
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_raw.sort_index(inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    ie = IndicatorEngine()
    df_5m['atr'] = ie.calculate_atr(df_5m)
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    signals = []
    for i in range(50, len(df_5m)-1):
        ts = df_5m.index[i]
        if ts.date() < start_d or ts.date() > end_d: continue
        if ts.time() > time(13, 30): continue # Time Gate

        r_info = regime_map.get(ts)
        if not r_info: continue
        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        # Selectivity Logic
        is_danger = (vix_filter.vix_direction in ["SPIKE", "RISING"]) or (r_info['regime'] in ["VOLATILE", "CHOPPY"])
        threshold = 85 if is_danger else 85 # Strict 85% everywhere
        
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
            
            if allowed and adj_conf >= threshold:
                base = get_base_data(df_5m, i)
                signals.append({
                    'ts': ts, 'symbol': symbol, 'dir': rev_dir, 'entry': base['price'], 'atr': base['atr'],
                    'hi_20': base['hi_20'], 'lo_20': base['lo_20'], 'df': df_5m, 'idx': i
                })
    return signals

def simulate_with_limits(all_signals, tp_type):
    # Sort signals chronologically
    signals = sorted(all_signals, key=lambda x: x['ts'])
    
    active_trades = [] # List of {symbol, exit_ts, net_pnl}
    daily_trade_count = {} # {date: count}
    total_net = 0
    trades_taken = 0
    wins = 0
    
    for s in signals:
        dt = s['ts'].date()
        if dt not in daily_trade_count: daily_trade_count[dt] = 0
        
        # Cleanup expired trades
        active_trades = [t for t in active_trades if t['exit_ts'] > s['ts']]
        
        # Enforce Constraints
        if daily_trade_count[dt] >= MAX_DAILY_TRADES: continue
        if len(active_trades) >= MAX_SIMULTANEOUS: continue
        if any(t['symbol'] == s['symbol'] for t in active_trades): continue
        
        # Parameters for this combo
        entry = s['entry']; atr = s['atr']; direction = s['dir']
        sl_dist = atr * 2.5
        sl_price = entry - sl_dist if direction == 'CE' else entry + sl_dist
        
        tp_price = 0
        if tp_type == "TP_FIX_2R": tp_price = entry + 2.0 * sl_dist if direction == 'CE' else entry - 2.0 * sl_dist
        elif tp_type == "TP_SR": tp_price = s['hi_20'] if direction == 'CE' else s['lo_20']
        else: # TP_MEASURED
             range_h = s['hi_20'] - s['lo_20']
             tp_price = entry + range_h if direction == 'CE' else entry - range_h

        qty = RISK_PER_TRADE / sl_dist
        if (qty * entry) > (INITIAL_CAPITAL * 5.0): qty = (INITIAL_CAPITAL * 5.0) / entry
        
        # Simulate Outcome
        exit_p = entry; exit_time = s['ts']; exit_reason = "EOD"
        df_5m = s['df']; i = s['idx']
        for j in range(i+1, len(df_5m)):
            if df_5m.index[j].date() != dt: break
            curr = df_5m.iloc[j]
            if direction == 'CE':
                if curr['Low'] <= sl_price: exit_p = sl_price; exit_time = df_5m.index[j]; exit_reason = "SL"; break
                if curr['High'] >= tp_price: exit_p = tp_price; exit_time = df_5m.index[j]; exit_reason = "TP"; break
            else:
                if curr['High'] >= sl_price: exit_p = sl_price; exit_time = df_5m.index[j]; exit_reason = "SL"; break
                if curr['Low'] <= tp_price: exit_p = tp_price; exit_time = df_5m.index[j]; exit_reason = "TP"; break
        
        if exit_reason == "EOD":
            exit_p = df_5m[df_5m.index.date == dt].iloc[-1]['Close']
            exit_time = df_5m[df_5m.index.date == dt].index[-1]
            
        costs = calc_costs(qty, entry, exit_p)
        gross = (exit_p - entry) * qty if direction == 'CE' else (entry - exit_p) * qty
        net = gross - costs
        
        active_trades.append({'symbol': s['symbol'], 'exit_ts': exit_time, 'net': net})
        daily_trade_count[dt] += 1
        total_net += net
        trades_taken += 1
        if net > 0: wins += 1
        
    return {'trades': trades_taken, 'net': total_net, 'wr': (wins/max(1,trades_taken))*100}

def main():
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    nifty_df = pd.read_csv('data/nifty50_5m.csv')
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    regime_gate = RegimeGate()
    regime_map = {}
    for i in range(100, len(nifty_df)):
        regime_gate.update_regime(nifty_df.iloc[max(0, i-150):i+1])
        regime_map[nifty_df.index[i]] = {'regime': regime_gate.current_regime}

    start_d = datetime(2026, 1, 8).date(); end_d = datetime(2026, 2, 19).date()
    
    print(f"Generating high-conviction signals (>85%) for {len(SYMBOLS)} stocks...")
    args = [(s, start_d, end_d, regime_map, vix_df) for s in SYMBOLS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(get_all_signals, args))
    all_sig = [sig for res in results for sig in res]
    
    print(f"Total High-Conviction Signals Found: {len(all_sig)}")
    print("\n--- CHRONOLOGICAL PORTFOLIO TEST (MAX 5 TRADES/DAY, MAX 2 ACTIVE) ---")
    print(f"{'Strategy':<15} | {'Trades':<8} | {'Win Rate':<8} | {'Total Net P&L':<15}")
    print("-" * 55)
    
    for tp in ["TP_SR", "TP_MEASURED", "TP_FIX_2R"]:
        res = simulate_with_limits(all_sig, tp)
        print(f"{tp:<15} | {res['trades']:<8} | {res['wr']:>7.1f}% | {res['net']:>15,.2f}")

if __name__ == "__main__":
    main()
