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
MAX_WORKERS = 4

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
        mode_label = "DANGER" if is_danger else "NORMAL"

        if is_danger and i >= 1:
            prev_bar = df_5m.iloc[i-1]
            range_pct = ((prev_bar['High'] - prev_bar['Low']) / prev_bar['Close']) * 100
            dead_thresh = 0.25 if prev_bar['Close'] > 1000 else 0.5
            if range_pct < dead_thresh:
                continue

        risk_pct = 0.005 if is_danger else 0.01
        base_sl_mult = 1.0 if is_danger else 0.5
        
        row = df_mr.iloc[i]
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': base_sl_mult}
        
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
                    score = sum(s['score'] for s in aligned)
                    bonus, _ = mr_engine._compute_bonuses(row, df_mr, i)
                    total_score = score + bonus
                    if total_score >= settings['min_score']:
                        conf = min(100, int(total_score * 10))
                        vix_direction = 'CE' if direction == 'LONG' else 'PE'
                        adj_conf, allowed, _ = vix_filter.filter_signal(vix_direction, conf)
                        if allowed and adj_conf >= 60:
                            sl, target, _ = mr_engine._calculate_sl_target(row, direction, aligned[0]['signal_type'], settings)
                            best_sig = {'strategy': 'MEAN_REVERSION', 'direction': vix_direction, 'entry': row['close'], 'sl': sl, 'target': target, 'confidence': adj_conf}

        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], min(100, int(mom_sig['score'] * 12)))
                if allowed and adj_conf >= 60:
                    dist = abs(mom_sig['entry'] - mom_sig['sl'])
                    actual_sl = mom_sig['sl']
                    if is_danger:
                        atr = row.get('atr', (df_5m.iloc[i]['High'] - df_5m.iloc[i]['Low']))
                        if mom_sig['direction'] == 'CE': actual_sl = min(actual_sl, mom_sig['entry'] - atr * 1.0)
                        else: actual_sl = max(actual_sl, mom_sig['entry'] + atr * 1.0)
                        dist = abs(mom_sig['entry'] - actual_sl)
                    
                    target = mom_sig['entry'] + (1.5 * dist) if mom_sig['direction'] == 'CE' else mom_sig['entry'] - (1.5 * dist)
                    best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': actual_sl, 'target': target, 'confidence': adj_conf}

        if best_sig:
            entry, sl, target = best_sig['entry'], best_sig['sl'], best_sig['target']
            risk = abs(entry - sl)
            if risk == 0: continue
            
            found = False; exit_time = None; outcome_r = 0
            exit_reason = "UNKNOWN"
            exit_p = entry
            
            for j in range(i+1, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                if best_sig['direction'] == 'CE':
                    if curr['Low'] <= sl: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; exit_p = sl; exit_reason = "SL"; break
                    if curr['High'] >= target: outcome_r = (target - entry)/risk; found = True; exit_time = df_5m.index[j]; exit_p = target; exit_reason = "TARGET"; break
                else:
                    if curr['High'] >= sl: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; exit_p = sl; exit_reason = "SL"; break
                    if curr['Low'] <= target: outcome_r = (entry - target)/risk; found = True; exit_time = df_5m.index[j]; exit_p = target; exit_reason = "TARGET"; break
            
            if not found:
                k = i
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date(): k += 1
                exit_time = df_5m.index[k]; exit_p = df_5m.iloc[k]['Close']
                exit_reason = "EOD"
                if exit_time <= ts: outcome_r = 0.0; exit_time = ts
                else: outcome_r = (exit_p - entry)/risk if best_sig['direction'] == 'CE' else (entry - exit_p)/risk

            last_exit_ts = exit_time
            trades.append({'ts': ts, 'symbol': symbol, 'r': outcome_r, 'strat': best_sig['strategy'], 'exit_ts': exit_time, 'confidence': best_sig['confidence'], 'entry': entry, 'sl': sl, 'target': target, 'exit_price': exit_p, 'exit_reason': exit_reason, 'risk': risk, 'mode': mode_label, 'risk_pct': risk_pct})
            
    return trades

def run_simulation(symbols, start_dt, end_dt, regime_map, vix_df):
    args = [(s, start_dt, end_dt, regime_map, vix_df) for s in symbols]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_symbol, args))
    all_trades = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    equity = INITIAL_CAPITAL
    mode_stats = {"NORMAL": {"trades": 0, "gross": 0.0, "costs": 0.0}, "DANGER": {"trades": 0, "gross": 0.0, "costs": 0.0}}
    daily_stats = {}
    
    decorated_trades = []
    for t in all_trades:
        d_str = t['ts'].strftime("%Y-%m-%d")
        if d_str not in daily_stats: daily_stats[d_str] = {'net_pnl': 0.0, 'trades': 0}
        
        risk_amt = equity * t['risk_pct']
        qty = risk_amt / t['risk']
        turnover = qty * (t['entry'] + t['exit_price'])
        brokerage = 40 + (turnover * 0.0002)
        
        gross = t['r'] * risk_amt
        net = gross - brokerage
        equity += net
        
        daily_stats[d_str]['net_pnl'] += net
        daily_stats[d_str]['trades'] += 1
        
        mode = t['mode']
        mode_stats[mode]['trades'] += 1
        mode_stats[mode]['gross'] += gross
        mode_stats[mode]['costs'] += brokerage
        
        t_copy = t.copy()
        t_copy['net_pnl'] = net
        decorated_trades.append(t_copy)
        
    return decorated_trades, daily_stats, mode_stats, equity

def main():
    print("Loading VIX and Nifty data...")
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    vix_df.sort_index(inplace=True)
    
    nifty_df = pd.read_csv('data/nifty50_5m.csv')
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    dates = nifty_df['Timestamp'].dt.date.unique()
    
    # --- TEST 1: 25-Day Validation (4 Stocks) ---
    print("\n=== TEST 1: 25-DAY VALIDATION (4 STOCKS) ===")
    test_dates_25 = dates[:25]
    start_25 = datetime.combine(test_dates_25[0], datetime.min.time())
    end_25 = datetime.combine(test_dates_25[-1], datetime.max.time())
    
    print("Pre-calculating Regime for Test 1...")
    regime_25 = get_regime_series(start_25, end_25)
    
    symbols_4 = ['RELIANCE', 'ICICIBANK', 'HDFCBANK', 'INFY']
    trades_4, daily_4, mode_4, eq_4 = run_simulation(symbols_4, start_25, end_25, regime_25, vix_df)
    
    if trades_4:
        print(f"\nTrade Log (TEST 1):")
        print(f"{'Time':<18} | {'Mode':<8} | {'Sym':<10} | {'Reason':<8} | {'Net PnL':<8}")
        print("-" * 60)
        for t in trades_4:
            print(f"{t['ts'].strftime('%Y-%m-%d %H:%M')} | {t['mode']:<8} | {t['symbol']:<10} | {t['exit_reason']:<8} | {t['net_pnl']:<8.2f}")
    else:
        print("\nNo trades taken in Test 1.")
    
    print("\nMODE SPLIT TABLE (TEST 1):")
    print(f"{'Mode':<10} | {'Trades':<8} | {'Gross PnL':<12} | {'Costs':<10} | {'Net PnL':<12}")
    print("-" * 60)
    for m in ["NORMAL", "DANGER"]:
        s = mode_4[m]
        print(f"{m:<10} | {s['trades']:<8} | {s['gross']:>12,.2f} | {s['costs']:>10,.2f} | {(s['gross']-s['costs']):>12,.2f}")
    print("-" * 60)
    total_net = (mode_4["NORMAL"]["gross"] - mode_4["NORMAL"]["costs"]) + (mode_4["DANGER"]["gross"] - mode_4["DANGER"]["costs"])
    print(f"{'TOTAL':<10} | {len(trades_4):<8} | {'':<12} | {'':<10} | {total_net:>12,.2f}")
    
    # --- TEST 2: 10-Day Dec Validation (30 Stocks) ---
    print("\n=== TEST 2: 10-DAY DEC VALIDATION (30 STOCKS) ===")
    start_dec = datetime(2025, 12, 1)
    end_dec = datetime(2025, 12, 12)
    regime_dec = get_regime_series(start_dec, end_dec)
    
    nifty_20 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'ITC', 'LT', 'AXISBANK', 'SBIN', 'BHARTIARTL', 'MARUTI', 'BAJFINANCE', 'HCLTECH', 'SUNPHARMA', 'ADANIENT', 'TITAN', 'ULTRACEMCO', 'NTPC', 'JSWSTEEL', 'POWERGRID']
    all_files = [f.split('_')[0] for f in os.listdir('data/angel_historical') if '_1m.csv' in f]
    symbols_30 = nifty_20 + [s for s in all_files if s not in nifty_20][:10]
    
    trades_30, daily_30, mode_30, eq_30 = run_simulation(symbols_30, start_dec, end_dec, regime_dec, vix_df)
    
    print("\nMODE SPLIT TABLE (TEST 2):")
    print(f"{'Mode':<10} | {'Trades':<8} | {'Gross PnL':<12} | {'Costs':<10} | {'Net PnL':<12}")
    print("-" * 60)
    for m in ["NORMAL", "DANGER"]:
        s = mode_30[m]
        print(f"{m:<10} | {s['trades']:<8} | {s['gross']:>12,.2f} | {s['costs']:>10,.2f} | {(s['gross']-s['costs']):>12,.2f}")
    print("-" * 60)
    total_net_dec = (mode_30["NORMAL"]["gross"] - mode_30["NORMAL"]["costs"]) + (mode_30["DANGER"]["gross"] - mode_30["DANGER"]["costs"])
    print(f"{'TOTAL':<10} | {len(trades_30):<8} | {'':<12} | {'':<10} | {total_net_dec:>12,.2f}")
    
    print(f"\nFinal Capital (30 stocks): INR {eq_30:,.2f}")
    print(f"Total Return: {((eq_30/INITIAL_CAPITAL)-1)*100:.2f}%")

if __name__ == "__main__":
    main()
