import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine

INITIAL_CAPITAL = 100000.0
SYMBOLS = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY']
RISK_PER_TRADE = 1000.0

# Precise Cost Formula
def calc_costs(qty, entry, exit_p):
    buy_t = qty * entry; sell_t = qty * exit_p
    costs = 40 + (sell_t * 0.00025) + ((buy_t + sell_t) * 0.0000345) + 7.2 + (buy_t * 0.00003) + ((buy_t + sell_t) * 0.000001)
    return costs

def process_symbol_firmness(args):
    symbol, start_dt, end_dt = args
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    ie = IndicatorEngine()
    df_5m['atr'] = ie.calculate_atr(df_5m)
    df_5m['ema_20'] = df_5m['Close'].ewm(span=20).mean()
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    
    trades = []
    last_exit_ts = df_5m.index[0]
    
    for i in range(50, len(df_5m)-1):
        ts = df_5m.index[i]
        if ts.date() < start_dt or ts.date() > end_dt: continue
        if ts <= last_exit_ts: continue
        
        # LIQUIDITY_TRAP Signal
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            direction = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            entry = df_5m.iloc[i]['Close']
            atr = df_5m.iloc[i]['atr']
            
            # SL Type: Hourly ATR Proxy (2.5x) for Risk Sizing, EMA20 for Exit
            sl_dist_for_qty = atr * 2.5
            qty = RISK_PER_TRADE / sl_dist_for_qty
            if (qty * entry) > (INITIAL_CAPITAL * 5.0): qty = (INITIAL_CAPITAL * 5.0) / entry
            if qty < 1: continue

            # TP Type: FIB 1.618
            tp_price = entry + 1.618 * sl_dist_for_qty if direction == 'CE' else entry - 1.618 * sl_dist_for_qty
            
            exit_p = entry; exit_time = ts; exit_reason = "EOD"
            for j in range(i+1, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                
                # SL Condition: Close beyond EMA20
                sl_hit = (curr['Close'] < curr['ema_20']) if direction == 'CE' else (curr['Close'] > curr['ema_20'])
                if sl_hit:
                    exit_reason = "SL_EMA20"; exit_p = curr['Close']; exit_time = df_5m.index[j]; break
                
                # TP Condition: Price hits FIB Target
                tp_hit = (curr['High'] >= tp_price) if direction == 'CE' else (curr['Low'] <= tp_price)
                if tp_hit:
                    exit_reason = "TP_FIB"; exit_p = tp_price; exit_time = df_5m.index[j]; break
            
            if exit_reason == "EOD":
                exit_p = df_5m[df_5m.index.date == ts.date()].iloc[-1]['Close']
                exit_time = df_5m[df_5m.index.date == ts.date()].index[-1]

            last_exit_ts = exit_time
            costs = calc_costs(qty, entry, exit_p)
            gross = (exit_p - entry) * qty if direction == 'CE' else (entry - exit_p) * qty
            trades.append({'date': ts.date(), 'net': gross - costs, 'win': (gross - costs) > 0})
            
    return trades

def run_cluster(start_date, end_date):
    args = [(s, start_date, end_date) for s in SYMBOLS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(process_symbol_firmness, args))
    all_t = [t for res in results for t in res]
    
    if not all_t: return 0, 0, 0
    
    net_pnl = sum(t['net'] for t in all_t)
    wr = sum(1 for t in all_t if t['win']) / len(all_t) * 100
    return net_pnl, wr, len(all_t)

def main():
    clusters = [
        (datetime(2025, 12, 1).date(), datetime(2025, 12, 12).date()), # Original
        (datetime(2025, 12, 24).date(), datetime(2026, 1, 7).date()),   # Cluster 2
        (datetime(2026, 2, 20).date(), datetime(2026, 3, 6).date())    # Cluster 3
    ]
    
    print("--- FIRMNESS VALIDATION: SL_EMA20 + TP_FIB ---")
    print(f"{'Cluster':<12} | {'Date Range':<25} | {'Trades':<6} | {'Win%':<6} | {'Net P&L':<10}")
    print("-" * 75)
    
    total_net = 0
    for i, (start, end) in enumerate(clusters):
        net, wr, count = run_cluster(start, end)
        total_net += net
        print(f"Set {i+1:<7} | {str(start)} to {str(end):<10} | {count:<6} | {wr:>5.1f}% | {net:>10,.2f}")
        
    print("-" * 75)
    print(f"FINAL FIRMNESS TOTAL (30 DAYS): INR {total_net:,.2f}")
    print(f"PROFITABILITY SCORE: {'PASS' if total_net > 0 else 'FAIL'}")

if __name__ == "__main__":
    main()
