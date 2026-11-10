import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.indicator_engine import IndicatorEngine
from modules.regime_gate import RegimeGate
from modules.vix_filter import VIXDirectionalFilter

INITIAL_CAPITAL = 100000.0
SYMBOLS = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY']
BROKERAGE_ROUND_TRIP = 87.0 # Estimated from V7

# --- Logic Modules ---

def get_base_data(df, i):
    """Extract structural data for the signal bar."""
    row = df.iloc[i]
    prev_20 = df.iloc[max(0, i-20):i+1]
    prev_5 = df.iloc[max(0, i-5):i+1]
    
    return {
        'price': row['Close'],
        'atr': row.get('atr', (row['High'] - row['Low'])),
        'hi_20': prev_20['High'].max(),
        'lo_20': prev_20['Low'].min(),
        'hi_5': prev_5['High'].max(),
        'lo_5': prev_5['Low'].min(),
        'ema_20': row.get('ema_20', row['Close']),
        'signal_h': row['High'],
        'signal_l': row['Low']
    }

def simulate_combination(df_5m, i, direction, sl_type, tp_type, base_data):
    entry = base_data['price']
    atr = base_data['atr']
    
    # 1. Calculate Initial SL
    sl_dist = 0
    if sl_type == "SL_ATR_2": sl_dist = 2.0 * atr
    elif sl_type == "SL_CAP_1": sl_dist = entry * 0.01
    elif sl_type == "SL_FIX_0_5": sl_dist = entry * 0.005
    elif sl_type == "SL_SR": sl_dist = abs(entry - (base_data['lo_20'] if direction == 'CE' else base_data['hi_20']))
    elif sl_type == "SL_SWING": sl_dist = abs(entry - (base_data['lo_5'] if direction == 'CE' else base_data['hi_5']))
    elif sl_type == "SL_CANDLE": sl_dist = abs(entry - (base_data['signal_l'] if direction == 'CE' else base_data['signal_h']))
    else: sl_dist = 1.5 * atr # Default
    
    if sl_dist == 0: sl_dist = 0.001 * entry # Safety
    
    sl_price = entry - sl_dist if direction == 'CE' else entry + sl_dist
    
    # 2. Calculate Initial TP
    tp_price = 0
    if tp_type == "TP_FIX_2R": tp_price = entry + 2.0 * sl_dist if direction == 'CE' else entry - 2.0 * sl_dist
    elif tp_type == "TP_SR": tp_price = base_data['hi_20'] if direction == 'CE' else base_data['lo_20']
    elif tp_type == "TP_FIB": tp_price = entry + 1.618 * sl_dist if direction == 'CE' else entry - 1.618 * sl_dist
    elif tp_type == "TP_MEASURED": 
        range_h = base_data['hi_20'] - base_data['lo_20']
        tp_price = entry + range_h if direction == 'CE' else entry - range_h
    else: tp_price = entry + 1.5 * sl_dist if direction == 'CE' else entry - 1.5 * sl_dist # Default
    
    # Resolving "SL_HALF_TP"
    if sl_type == "SL_HALF_TP":
        tp_dist = abs(tp_price - entry)
        sl_dist = tp_dist / 2.0
        sl_price = entry - sl_dist if direction == 'CE' else entry + sl_dist

    # 3. Execution Simulation
    be_active = False
    trail_active = (tp_type in ["TP_TRAIL", "TP_PARTIAL"])
    partial_booked = False
    
    gross_pnl = 0
    exit_reason = "EOD"
    
    # Logic for Risk-Sized (1% of cap)
    qty = 1000.0 / sl_dist # Risking ₹1000 per trade
    # Leverage Cap 5x
    if (qty * entry) > (INITIAL_CAPITAL * 5.0):
        qty = (INITIAL_CAPITAL * 5.0) / entry

    for j in range(i+1, len(df_5m)):
        if df_5m.index[j].date() != df_5m.index[i].date(): break
        curr = df_5m.iloc[j]
        
        # SL Check
        if direction == 'CE':
            # Trailing SL update
            if trail_active:
                new_sl = curr['Close'] - 1.5 * atr
                if new_sl > sl_price: sl_price = new_sl
            
            if curr['Low'] <= sl_price:
                exit_reason = "SL"
                gross_pnl = (sl_price - entry) * qty if not partial_booked else (0.5 * (tp_price - entry) * qty) + (0.5 * (sl_price - entry) * qty)
                break
            
            # TP Check
            if not partial_booked and tp_type == "TP_PARTIAL" and curr['High'] >= (entry + sl_dist):
                partial_booked = True
                sl_price = entry # Move to BE
            
            if curr['High'] >= tp_price and tp_type != "TP_TRAIL":
                exit_reason = "TP"
                gross_pnl = (tp_price - entry) * qty
                break
        else:
            if trail_active:
                new_sl = curr['Close'] + 1.5 * atr
                if new_sl < sl_price: sl_price = new_sl

            if curr['High'] >= sl_price:
                exit_reason = "SL"
                gross_pnl = (entry - sl_price) * qty if not partial_booked else (0.5 * (entry - tp_price) * qty) + (0.5 * (entry - sl_price) * qty)
                break
                
            if not partial_booked and tp_type == "TP_PARTIAL" and curr['Low'] <= (entry - sl_dist):
                partial_booked = True
                sl_price = entry

            if curr['Low'] <= tp_price and tp_type != "TP_TRAIL":
                exit_reason = "TP"
                gross_pnl = (entry - tp_price) * qty
                break
                
        # Time-based overrides
        if sl_type == "SL_TIME" and (j - i) >= 6:
            pnl_now = (curr['Close'] - entry) if direction == 'CE' else (entry - curr['Close'])
            if pnl_now < 0:
                exit_reason = "TIME"
                gross_pnl = pnl_now * qty
                break

    if gross_pnl == 0: # EOD
        final_close = df_5m[df_5m.index.date == df_5m.index[i].date()].iloc[-1]['Close']
        gross_pnl = (final_close - entry) * qty if direction == 'CE' else (entry - final_close) * qty

    return gross_pnl - BROKERAGE_ROUND_TRIP

def process_symbol(symbol):
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    # Indicators
    ie = IndicatorEngine()
    df_5m['atr'] = ie.calculate_atr(df_5m)
    df_5m['ema_20'] = df_5m['Close'].ewm(span=20).mean()
    
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    
    sl_strats = ["SL_HALF_TP", "SL_CAP_1", "SL_SR", "SL_SWING", "SL_ATR_2", "SL_FIX_0_5", "SL_CANDLE", "SL_EMA20", "SL_RISK_1", "SL_TIME"]
    tp_strats = ["TP_FIX_2R", "TP_SR", "TP_TRAIL", "TP_PARTIAL", "TP_MEASURED", "TP_FIB", "TP_STALL"]
    
    results = { (sl, tp): [] for sl in sl_strats for tp in tp_strats }
    
    start_dt = pd.Timestamp("2025-12-01").tz_localize('Asia/Kolkata')
    end_dt = pd.Timestamp("2025-12-12").tz_localize('Asia/Kolkata')
    
    for i in range(50, len(df_5m)-1):
        ts = df_5m.index[i]
        if ts < start_dt or ts > end_dt: continue
        
        # LIQUIDITY_TRAP Signal
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            # Signal direction FADED
            direction = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            base_data = get_base_data(df_5m, i)
            
            for sl in sl_strats:
                for tp in tp_strats:
                    net_pnl = simulate_combination(df_5m, i, direction, sl, tp, base_data)
                    results[(sl, tp)].append(net_pnl)
                    
    return results

def main():
    print("Starting Grid Search on 4 Stocks, 10 Days (70 Combinations)...")
    with ProcessPoolExecutor(max_workers=4) as executor:
        all_results = list(executor.map(process_symbol, SYMBOLS))
    
    # Merge results
    final_table = []
    sl_strats = ["SL_HALF_TP", "SL_CAP_1", "SL_SR", "SL_SWING", "SL_ATR_2", "SL_FIX_0_5", "SL_CANDLE", "SL_EMA20", "SL_RISK_1", "SL_TIME"]
    tp_strats = ["TP_FIX_2R", "TP_SR", "TP_TRAIL", "TP_PARTIAL", "TP_MEASURED", "TP_FIB", "TP_STALL"]

    print("\n| SL Strategy | TP Strategy | Trades | Total Net P&L | Win Rate | Avg Net/Trade |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")

    for sl in sl_strats:
        for tp in tp_strats:
            combined_pnls = []
            for res in all_results:
                combined_pnls.extend(res[(sl, tp)])
            
            if not combined_pnls: continue
            
            total_net = sum(combined_pnls)
            win_rate = sum(1 for p in combined_pnls if p > 0) / len(combined_pnls) * 100
            avg_net = total_net / len(combined_pnls)
            
            final_table.append({
                'sl': sl, 'tp': tp, 'trades': len(combined_pnls), 
                'net': total_net, 'wr': win_rate, 'avg': avg_net
            })
            
    # Output every result
    for r in sorted(final_table, key=lambda x: x['net'], reverse=True):
        print(f"| {r['sl']:<12} | {r['tp']:<12} | {r['trades']:<6} | {r['net']:>13,.2f} | {r['wr']:>7.1f}% | {r['avg']:>13,.2f} |")

if __name__ == "__main__":
    main()
