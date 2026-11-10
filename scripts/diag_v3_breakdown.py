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

def is_stock_tradeable(df_stock):
    latest = df_stock.iloc[-1]
    range_pct = ((latest['High'] - latest['Low']) / latest['Close']) * 100
    if range_pct < 0.5: return (False, 'DEAD')
    if range_pct > 4.0: return (True, 'HIGH')
    return (True, 'NORMAL')

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    data_path = f'data/angel_historical/{symbol}_1m.csv'
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna().between_time('09:15', '15:30')
    
    mr_engine = MeanReversionEngine()
    df_mr = mr_engine._compute_indicators(df_5m)
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    vix_filter = VIXDirectionalFilter(config_path='config/vix_filter.yaml')
    
    trades = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist or ts.strftime('%Y-%m-%d') > '2025-12-12': continue
        
        tradeable, stock_vol = is_stock_tradeable(df_5m.iloc[:i+1])
        if not tradeable or ts <= last_exit_ts: continue
        
        r_info = regime_map.get(ts)
        if not r_info: continue
        
        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        row = df_mr.iloc[i]
        base_mr_sl_mult = 1.0 if stock_vol == 'HIGH' else 0.5
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': base_mr_sl_mult}
        
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
                    if total_score >= settings['min_score']:
                        conf = min(100, int(total_score * 10))
                        adj_conf, allowed, _ = vix_filter.filter_signal('CE' if direction == 'LONG' else 'PE', conf)
                        if allowed and adj_conf >= 60:
                            sl, target, _ = mr_engine._calculate_sl_target(row, direction, aligned[0]['signal_type'], settings)
                            best_sig = {'strategy': 'MEAN_REVERSION', 'direction': 'CE' if direction == 'LONG' else 'PE', 'entry': row['close'], 'sl': sl, 'target': target}
        
        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], min(100, int(mom_sig['score'] * 12)))
                if allowed and adj_conf >= 60:
                    dist = abs(mom_sig['entry'] - mom_sig['sl'])
                    if stock_vol == 'HIGH':
                        atr = row.get('atr', (df_5m.iloc[i]['High'] - df_5m.iloc[i]['Low']))
                        if mom_sig['direction'] == 'CE': mom_sig['sl'] = min(mom_sig['sl'], mom_sig['entry'] - atr * 1.0)
                        else: mom_sig['sl'] = max(mom_sig['sl'], mom_sig['entry'] + atr * 1.0)
                    best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': mom_sig['sl'], 'target': mom_sig['entry'] + (1.5 * dist if mom_sig['direction'] == 'CE' else -1.5 * dist)}
        
        if best_sig:
            found = False; outcome_r = 0; exit_time = None
            for j in range(i+1, len(df_5m)):
                if df_5m.index[j].date() != ts.date(): break
                curr = df_5m.iloc[j]
                if best_sig['direction'] == 'CE':
                    if curr['Low'] <= best_sig['sl']: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; break
                    if curr['High'] >= best_sig['target']: outcome_r = (best_sig['target'] - best_sig['entry'])/abs(best_sig['entry'] - best_sig['sl']); found = True; exit_time = df_5m.index[j]; break
                else:
                    if curr['High'] >= best_sig['sl']: outcome_r = -1.0; found = True; exit_time = df_5m.index[j]; break
                    if curr['Low'] <= best_sig['target']: outcome_r = (best_sig['entry'] - best_sig['target'])/abs(best_sig['entry'] - best_sig['sl']); found = True; exit_time = df_5m.index[j]; break
            if not found:
                k = i;
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date(): k += 1
                exit_time = df_5m.index[k]; exit_p = df_5m.iloc[k]['Close']
                if exit_time <= ts: outcome_r = 0.0; exit_time = ts
                else: outcome_r = (exit_p - best_sig['entry'])/abs(best_sig['entry'] - best_sig['sl']) if best_sig['direction'] == 'CE' else (best_sig['entry'] - exit_p)/abs(best_sig['entry'] - best_sig['sl'])
            last_exit_ts = exit_time
            trades.append({'ts': ts, 'r': outcome_r, 'strat': best_sig['strategy']})
    return trades

if __name__ == '__main__':
    nifty_path = 'data/nifty50_5m.csv'
    df_nifty_raw = pd.read_csv(nifty_path)
    df_nifty_raw['Timestamp'] = pd.to_datetime(df_nifty_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_nifty_raw.set_index('Timestamp', inplace=True)
    df_nifty = df_nifty_raw.between_time('09:15', '15:30')
    
    regime_gate = RegimeGate()
    regime_map = {}
    for i in range(100, len(df_nifty)):
        ts = df_nifty.index[i]
        if ts < pd.Timestamp('2025-12-01').tz_localize('Asia/Kolkata'): continue
        regime_gate.update_regime(df_nifty.iloc[max(0, i-150):i+1])
        regime_map[ts] = {'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION']}}

    vix_df = pd.read_csv('data/indiavix_5m.csv')
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    
    symbols = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'ITC', 'LT', 'AXISBANK', 'SBIN', 'BHARTIARTL', 'MARUTI', 'BAJFINANCE', 'HCLTECH', 'SUNPHARMA', 'ADANIENT', 'TITAN', 'ULTRACEMCO', 'NTPC', 'JSWSTEEL', 'POWERGRID']
    all_files = [f.split('_')[0] for f in os.listdir('data/angel_historical') if '_1m.csv' in f]
    symbols += [s for s in all_files if s not in symbols][:10]

    args = [(s, datetime(2025, 12, 1), datetime(2025, 12, 12), regime_map, vix_df) for s in symbols]
    with ProcessPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(process_symbol, args))
    
    all_trades = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    # 1. Trade Breakdown
    breakdown = {}
    for t in all_trades:
        breakdown[t['strat']] = breakdown.get(t['strat'], 0) + 1
    print(f"Trade Breakdown: {breakdown}")
    print(f"Total Trades: {len(all_trades)}")
    
    # 2. Daily Returns for Ratios
    equity = 100000.0
    daily_equity = {pd.Timestamp('2025-12-01').date(): 100000.0}
    for t in all_trades:
        risk = equity * 0.01
        equity += t['r'] * risk
        daily_equity[t['ts'].date()] = equity
    
    df_eq = pd.Series(daily_equity).sort_index()
    returns = df_eq.pct_change().dropna()
    avg_ret = returns.mean()
    std_ret = returns.std()
    sharpe = (avg_ret / std_ret * np.sqrt(252)) if std_ret != 0 else 0
    
    total_ret = (df_eq.iloc[-1] / df_eq.iloc[0]) - 1
    # Max DD
    roll_max = df_eq.cummax()
    drawdown = (df_eq - roll_max) / roll_max
    max_dd = abs(drawdown.min())
    calmar = (total_ret * 25) / max_dd if max_dd != 0 else 0 # Annualized (10 days * 25 = 250 days)
    
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Calmar Ratio: {calmar:.2f}")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
