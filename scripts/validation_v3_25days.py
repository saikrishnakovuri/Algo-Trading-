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

# --- Validation Config ---
INITIAL_CAPITAL = 100000.0
RISK_PER_TRADE_PCT = 0.01 
MAX_WORKERS = 4
SYMBOLS = ['RELIANCE', 'ICICIBANK', 'HDFCBANK', 'INFY']

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

def is_stock_tradeable(df_stock: pd.DataFrame) -> tuple:
    """Quick per-stock vol check BEFORE running expensive strategy engines."""
    if len(df_stock) < 2:
        return (True, "NORMAL")
    # Uses previous bar (iloc[-2]) to avoid look-ahead bias
    latest = df_stock.iloc[-2]
    range_pct = ((latest['High'] - latest['Low']) / latest['Close']) * 100
    if range_pct < 0.5:
        return (False, "DEAD_STOCK")
    if range_pct > 4.0:
        return (True, "HIGH_VOL_STOCK")
    return (True, "NORMAL")

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
        
        # Look-ahead Fix inclusion
        tradeable, stock_vol = is_stock_tradeable(df_5m.iloc[:i+1])
        if not tradeable or ts <= last_exit_ts:
            continue

        r_info = regime_map.get(ts)
        if not r_info: continue

        vix_slice = vix_df[vix_df.index <= ts].tail(20)
        vix_filter.update(vix_slice)

        row = df_mr.iloc[i]
        base_mr_sl_mult = 1.0 if stock_vol == "HIGH_VOL_STOCK" else 0.5
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
                score = mom_sig['score']
                conf = min(100, int(score * 12))
                adj_conf, allowed, _ = vix_filter.filter_signal(mom_sig['direction'], conf)
                if allowed and adj_conf >= 60:
                    dist = abs(mom_sig['entry'] - mom_sig['sl'])
                    if stock_vol == "HIGH_VOL_STOCK":
                        atr = row.get('atr', (df_5m.iloc[i]['High'] - df_5m.iloc[i]['Low']))
                        if mom_sig['direction'] == 'CE': mom_sig['sl'] = min(mom_sig['sl'], mom_sig['entry'] - atr * 1.0)
                        else: mom_sig['sl'] = max(mom_sig['sl'], mom_sig['entry'] + atr * 1.0)
                    best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': mom_sig['sl'], 'target': mom_sig['entry'] + (1.5 * dist if mom_sig['direction'] == 'CE' else -1.5 * dist), 'confidence': adj_conf}

        if best_sig:
            entry, sl, target = best_sig['entry'], best_sig['sl'], best_sig['target']
            risk = abs(entry - sl)
            if risk == 0: continue
            
            found = False; exit_time = None; outcome_r = 0
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
                exit_time = df_5m.index[k]; exit_p = df_5m.iloc[k]['Close']
                if exit_time <= ts: outcome_r = 0.0; exit_time = ts
                else: outcome_r = (exit_p - entry)/risk if best_sig['direction'] == 'CE' else (entry - exit_p)/risk

            last_exit_ts = exit_time
            trades.append({'ts': ts, 'symbol': symbol, 'r': outcome_r, 'strat': best_sig['strategy'], 'exit_ts': exit_time, 'confidence': best_sig['confidence']})
            
    return trades

def main():
    print("Loading VIX and Nifty data...")
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    vix_df.sort_index(inplace=True)
    
    # Define the 25 sessions
    nifty_df = pd.read_csv('data/nifty50_5m.csv')
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    dates = nifty_df['Timestamp'].dt.date.unique()
    test_dates = dates[:25]
    start_dt = datetime.combine(test_dates[0], datetime.min.time())
    end_dt = datetime.combine(test_dates[-1], datetime.max.time())
    
    print(f"Validation Period: {test_dates[0]} to {test_dates[-1]} (25 Sessions)")
    regime_map = get_regime_series(start_dt, end_dt)
    
    args = [(s, start_dt, end_dt, regime_map, vix_df) for s in SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_symbol, args))
    
    all_trades = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    # Final Analysis
    equity = INITIAL_CAPITAL
    daily_stats = {} # date: {pnl, trades, wins, losses}
    symbol_stats = {s: {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'r_sum': 0.0} for s in SYMBOLS}
    
    streak = 0; max_win_streak = 0; max_loss_streak = 0
    current_streak_type = None # 'win' or 'loss'
    
    gross_wins = 0.0; gross_losses = 0.0
    
    for t in all_trades:
        d_str = t['ts'].strftime("%Y-%m-%d")
        if d_str not in daily_stats: daily_stats[d_str] = {'pnl': 0.0, 'trades': 0, 'wins': 0, 'losses': 0}
        
        risk_amt = equity * RISK_PER_TRADE_PCT
        pnl = t['r'] * risk_amt
        equity += pnl
        
        daily_stats[d_str]['pnl'] += pnl
        daily_stats[d_str]['trades'] += 1
        
        symbol_stats[t['symbol']]['trades'] += 1
        symbol_stats[t['symbol']]['pnl'] += pnl
        symbol_stats[t['symbol']]['r_sum'] += t['r']
        
        if pnl > 0:
            daily_stats[d_str]['wins'] += 1
            symbol_stats[t['symbol']]['wins'] += 1
            gross_wins += pnl
            if current_streak_type == 'win': streak += 1
            else: streak = 1; current_streak_type = 'win'
            max_win_streak = max(max_win_streak, streak)
        else:
            daily_stats[d_str]['losses'] += 1
            symbol_stats[t['symbol']]['losses'] += 1
            gross_losses += abs(pnl)
            if current_streak_type == 'loss': streak += 1
            else: streak = 1; current_streak_type = 'loss'
            max_loss_streak = max(max_loss_streak, streak)

    # 1. Daily P&L Table
    print("\n1. DAILY P&L TABLE")
    print(f"{'Day':<4} | {'Date':<12} | {'Capital':<12} | {'Return %':<8} | {'Trades':<8} | {'W/L'}")
    print("-" * 65)
    running_eq = INITIAL_CAPITAL
    for i, d in enumerate(test_dates):
        d_str = d.strftime("%Y-%m-%d")
        stats = daily_stats.get(d_str, {'pnl': 0.0, 'trades': 0, 'wins': 0, 'losses': 0})
        day_ret = (stats['pnl'] / running_eq) * 100
        running_eq += stats['pnl']
        print(f"{i+1:<4} | {d_str:<12} | {running_eq:<12,.2f} | {day_ret:>7.2f}% | {stats['trades']:<8} | {stats['wins']}/{stats['losses']}")

    # 2. Per-stock breakdown
    print("\n2. PER-STOCK BREAKDOWN")
    print(f"{'Stock':<12} | {'Trades':<6} | {'Wins':<5} | {'Losses':<6} | {'Net P&L':<12} | {'Avg R'}")
    print("-" * 65)
    for s in SYMBOLS:
        st = symbol_stats[s]
        avg_r = st['r_sum'] / st['trades'] if st['trades'] > 0 else 0
        print(f"{s:<12} | {st['trades']:<6} | {st['wins']:<5} | {st['losses']:<6} | {st['pnl']:>12,.2f} | {avg_r:>6.2f}")

    # 3. Summary metrics
    total_trades = sum(st['trades'] for st in symbol_stats.values())
    win_rate = (sum(st['wins'] for st in symbol_stats.values()) / total_trades * 100) if total_trades > 0 else 0
    total_ret_pct = ((equity / INITIAL_CAPITAL) - 1) * 100
    
    # DD
    eq_curve = [INITIAL_CAPITAL]
    curr = INITIAL_CAPITAL
    for t in all_trades:
        curr += t['r'] * (curr * RISK_PER_TRADE_PCT)
        eq_curve.append(curr)
    
    dd_pct = 0; max_dd = 0; dd_date = test_dates[0]
    peak = INITIAL_CAPITAL
    for i, val in enumerate(eq_curve):
        if val > peak: peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd
            # Find which date this trade belonged to
            if i > 0: dd_date = all_trades[i-1]['ts'].date()
            
    avg_win = gross_wins / sum(st['wins'] for st in symbol_stats.values()) if sum(st['wins'] for st in symbol_stats.values()) > 0 else 0
    avg_loss = gross_losses / sum(st['losses'] for st in symbol_stats.values()) if sum(st['losses'] for st in symbol_stats.values()) > 0 else 0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float('inf')
    expectancy = (gross_wins - gross_losses) / total_trades if total_trades > 0 else 0

    print("\n3. SUMMARY METRICS")
    print(f"- Final capital: INR {equity:,.2f}")
    print(f"- Total return %: {total_ret_pct:.2f}%")
    print(f"- Max drawdown %: {max_dd:.2f}% (on {dd_date})")
    print(f"- Win rate %: {win_rate:.2f}%")
    print(f"- Average winner: INR {avg_win:,.2f}")
    print(f"- Average loser: INR {avg_loss:,.2f}")
    print(f"- Profit factor: {profit_factor:.2f}")
    print(f"- Expectancy per trade: INR {expectancy:,.2f}")
    print(f"- Longest win streak: {max_win_streak}")
    print(f"- Longest loss streak: {max_loss_streak}")

    # 4. Regime Context
    print("\n4. REGIME CONTEXT (Weekly)")
    week_start = test_dates[0]
    current_week = 1
    for i in range(0, len(test_dates), 5):
        w_dates = test_dates[i:i+5]
        w_str = f"Week {current_week} ({w_dates[0]} to {w_dates[-1]})"
        # Representative regime (middle of week)
        mid_ts = pd.Timestamp(datetime.combine(w_dates[len(w_dates)//2], datetime.strptime("12:00:00", "%H:%M:%S").time())).tz_localize('Asia/Kolkata')
        r_info = regime_map.get(mid_ts, {'regime': 'UNKNOWN'})
        print(f"{w_str:<40} | Regime: {r_info['regime']}")
        current_week += 1

    # 5. Equity Curve (CSV)
    print("\n5. EQUITY CURVE (Daily Closing)")
    print("Date,Capital")
    curr_eq = INITIAL_CAPITAL
    for d in test_dates:
        d_str = d.strftime("%Y-%m-%d")
        curr_eq += daily_stats.get(d_str, {'pnl': 0.0})['pnl']
        print(f"{d_str},{curr_eq:.2f}")

if __name__ == "__main__":
    main()
