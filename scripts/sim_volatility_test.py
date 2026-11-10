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

# === EVENT CALENDAR START ===
# REVERT: Comment out to disable event calendar in backtest
from modules.event_calendar import EventCalendar
event_cal = EventCalendar("config/no_trade_dates.yaml")
# === EVENT CALENDAR END ===

# --- Simulation Config ---
INITIAL_CAPITAL = 100000.0
RISK_PER_TRADE_PCT = 0.01 
MAX_WORKERS = 4

HIGH_VOL_DATES = [
    "2026-01-16", "2026-01-30", "2026-02-01", "2026-03-04", 
    "2026-04-04", "2026-04-05", "2026-04-22"
]

LOW_VOL_DATES = [
    "2026-01-08", "2026-01-09", "2026-01-10", "2026-02-03", 
    "2026-02-27", "2026-02-28", "2026-03-12", "2026-04-09", "2026-04-10"
]

ALL_TEST_DATES = sorted(list(set(HIGH_VOL_DATES + LOW_VOL_DATES)))

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
            'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION']}
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
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist: continue
        if ts.strftime("%Y-%m-%d") not in ALL_TEST_DATES: continue
        
        # === EVENT CALENDAR START ===
        # REVERT: Comment out this block to disable event calendar blocking in backtest
        today_str = ts.strftime('%Y-%m-%d')
        if not event_cal.should_allow_entries(today_str):
            continue
        if event_cal.is_symbol_blocked(symbol, today_str):
            continue
        # === EVENT CALENDAR END ===

        if ts <= last_exit_ts: continue

        r_info = regime_map.get(ts)
        if not r_info: continue

        vix_slice = vix_df[vix_df.index <= ts].tail(20)
        vix_filter.update(vix_slice)

        row = df_mr.iloc[i]
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': 0.5}
        trend_ok, _ = mr_engine._check_anti_trend_filter(row)
        best_sig = None
        
        if trend_ok:
            bb = mr_engine._check_bb_reversion(row, settings)
            vwap = mr_engine._check_vwap_reversion(row, settings)
            rsi = mr_engine._check_rsi_extreme(row, settings)
            fired = [s for s in [bb, vwap, rsi] if s is not None]
            
            if fired:
                long_v = sum(1 for s in fired if s['direction'] == 'LONG')
                short_v = sum(1 for s in fired if s['direction'] == 'SHORT')
                direction = 'LONG' if long_v > short_v else ('SHORT' if short_v > long_v else None)
                if direction and r_info['allowed']['MEAN_REVERSION']:
                    aligned = [s for s in fired if s['direction'] == direction]
                    score = sum(s['score'] for s in aligned)
                    bonus, _ = mr_engine._compute_bonuses(row, df_mr, i)
                    total_score = score + bonus
                    conf = min(100, int(total_score * 10))
                    
                    vix_direction = 'CE' if direction == 'LONG' else 'PE'
                    adj_conf, allowed, reason = vix_filter.filter_signal(vix_direction, conf)
                    if allowed and adj_conf >= 60:
                        sl, target, _ = mr_engine._calculate_sl_target(row, direction, aligned[0]['signal_type'], settings)
                        best_sig = {'strategy': 'MEAN_REVERSION', 'direction': vix_direction, 'entry': row['close'], 'sl': sl, 'target': target}

        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                score = mom_sig['score']
                conf = min(100, int(score * 12))
                adj_conf, allowed, reason = vix_filter.filter_signal(mom_sig['direction'], conf)
                if allowed and adj_conf >= 60:
                    dist = abs(mom_sig['entry'] - mom_sig['sl'])
                    target = mom_sig['entry'] + (1.5 * dist) if mom_sig['direction'] == 'CE' else mom_sig['entry'] - (1.5 * dist)
                    best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': mom_sig['sl'], 'target': target}

        if best_sig:
            entry, sl, target = best_sig['entry'], best_sig['sl'], best_sig['target']
            risk = abs(entry - sl)
            if risk == 0: continue
            
            found = False
            exit_time = None
            outcome_r = 0
            
            for j in range(i+1, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                if best_sig['direction'] == 'CE':
                    if curr['Low'] <= sl: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; break
                    if curr['High'] >= target: outcome_r = (target - entry)/risk; found = True; exit_time = df_5m.index[j]; break
                else:
                    if curr['High'] >= sl: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; break
                    if curr['Low'] <= target: outcome_r = (entry - target)/risk; found = True; exit_time = df_5m.index[j]; break
            
            if not found:
                k = i
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date(): k += 1
                exit_time = df_5m.index[k]
                exit_p = df_5m.iloc[k]['Close']
                if exit_time <= ts: outcome_r = 0.0; exit_time = ts
                else: outcome_r = (exit_p - entry)/risk if best_sig['direction'] == 'CE' else (entry - exit_p)/risk

            last_exit_ts = exit_time
            trades.append({'ts': ts, 'symbol': symbol, 'r': outcome_r, 'strat': best_sig['strategy'], 'exit_ts': exit_time})
            
    return trades

def main():
    print("Loading VIX and Nifty data...")
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    vix_df.sort_index(inplace=True)
    
    start_dt = datetime(2026, 1, 1)
    end_dt = datetime(2026, 4, 30)
    regime_map = get_regime_series(start_dt, end_dt)
    
    symbols = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY']
    print(f"Running Volatility Stress Test for {symbols}...")
    
    args = [(s, start_dt, end_dt, regime_map, vix_df) for s in symbols]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_symbol, args))
    
    all_trades = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    equity = INITIAL_CAPITAL
    daily_results = {} # date: pnl_inr
    
    for t in all_trades:
        d_str = t['ts'].strftime("%Y-%m-%d")
        risk_amt = equity * 0.01
        pnl = t['r'] * risk_amt
        equity += pnl
        daily_results[d_str] = daily_results.get(d_str, 0) + pnl

    print("\n--- VOLATILITY STRESS TEST RESULTS ---")
    print(f"{'Date':<15} | {'Type':<10} | {'PnL (INR)':<12} | {'Equity':<12}")
    print("-" * 55)
    
    total_high_pnl = 0
    total_low_pnl = 0
    
    running_equity = INITIAL_CAPITAL
    for d in ALL_TEST_DATES:
        pnl = daily_results.get(d, 0)
        running_equity += pnl
        vtype = "HIGH" if d in HIGH_VOL_DATES else "LOW"
        if vtype == "HIGH": total_high_pnl += pnl
        else: total_low_pnl += pnl
        print(f"{d:<15} | {vtype:<10} | {pnl:>12,.2f} | {running_equity:>12,.2f}")

    print("-" * 55)
    print(f"Total High Vol PnL: INR {total_high_pnl:,.2f}")
    print(f"Total Low Vol PnL:  INR {total_low_pnl:,.2f}")
    print(f"Final Total Equity: INR {running_equity:,.2f}")
    print(f"Total Return: {((running_equity/INITIAL_CAPITAL)-1)*100:.2f}%")

if __name__ == "__main__":
    main()
