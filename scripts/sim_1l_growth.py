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

# === VIX FILTER START ===
# REVERT: Comment out this import to disable VIX filter
from modules.vix_filter import VIXDirectionalFilter
# === VIX FILTER END ===

# --- Simulation Config ---
INITIAL_CAPITAL = 100000.0
RISK_PER_TRADE_PCT = 0.01 
MAX_WORKERS = 8

def get_regime_series(start_date, end_date):
    nifty_path = "data/nifty50_5m.csv"
    df_nifty_raw = pd.read_csv(nifty_path)
    df_nifty_raw['Timestamp'] = pd.to_datetime(df_nifty_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_nifty_raw.set_index('Timestamp', inplace=True)
    df_nifty_raw = df_nifty_raw.between_time('09:15', '15:30')
    
    start_ist = pd.Timestamp(start_date).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_date).tz_localize('Asia/Kolkata')
    df_nifty = df_nifty_raw[(df_nifty_raw.index >= start_ist - timedelta(days=10)) & (df_nifty_raw.index <= end_ist)]
    
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

def is_stock_tradeable(df_stock: pd.DataFrame) -> tuple:
    """Quick per-stock vol check BEFORE running expensive strategy engines."""
    # Safety: If less than 2 bars, skip filter to avoid index error
    if len(df_stock) < 2:
        return (True, "NORMAL")
        
    # Uses previous bar (iloc[-2]) to avoid look-ahead bias
    latest = df_stock.iloc[-2]
    range_pct = ((latest['High'] - latest['Low']) / latest['Close']) * 100
    
    # Too quiet — stock isn't moving enough to trade
    if range_pct < 0.5:
        return (False, "DEAD_STOCK")  # Skip: no opportunity
    
    # Too wild — stock is in event-driven chaos (use wider SL)
    if range_pct > 4.0:
        return (True, "HIGH_VOL_STOCK")  # Trade but widen SL to 1.0× ATR
    
    return (True, "NORMAL")

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    print(f"Analyzing {symbol}...")
    sys.stdout.flush()
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_raw.sort_index(inplace=True)
    
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    # Pre-calculate indicators
    mr_engine = MeanReversionEngine()
    df_mr = mr_engine._compute_indicators(df_5m)
    
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)

    # === VIX FILTER START ===
    # REVERT: Comment out these 2 lines to disable VIX filter in backtest
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    # === VIX FILTER END ===
    
    trades = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    
    # Position Lock: Prevent multiple simultaneous trades on same symbol
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist: continue
        
        # === PER-STOCK VOLATILITY FILTER START ===
        # REVERT: Comment out this block to disable per-stock volatility check
        tradeable, stock_vol = is_stock_tradeable(df_5m.iloc[:i+1])
        if not tradeable:
            continue
        # === PER-STOCK VOLATILITY FILTER END ===

        # Position Lock Check
        if ts <= last_exit_ts:
            continue

        r_info = regime_map.get(ts)
        if not r_info: continue

        # === VIX FILTER START ===
        # REVERT: Comment out this block to disable VIX directional bias
        vix_slice = vix_df[vix_df.index <= ts].tail(20)
        vix_filter.update(vix_slice)
        # === VIX FILTER END ===

        # 1. MEAN REVERSION CHECK
        row = df_mr.iloc[i]
        
        # === PER-STOCK VOLATILITY FILTER START ===
        # REVERT: Use static sl_atr_mult=0.5 to disable dynamic SL
        base_mr_sl_mult = 1.0 if stock_vol == "HIGH_VOL_STOCK" else 0.5
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': base_mr_sl_mult}
        # === PER-STOCK VOLATILITY FILTER END ===
        
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
                    if total_score >= settings['min_score']:
                        conf = min(100, int(total_score * 10))

                        # === VIX FILTER START ===
                        # REVERT: Comment out this block to disable VIX filter logic
                        vix_direction = 'CE' if direction == 'LONG' else 'PE'
                        adj_conf, allowed, reason = vix_filter.filter_signal(vix_direction, conf)
                        if not allowed:
                            continue
                        conf = adj_conf
                        # === VIX FILTER END ===

                        if conf >= 60:
                            sl, target, _ = mr_engine._calculate_sl_target(row, direction, aligned[0]['signal_type'], settings)
                            best_sig = {'strategy': 'MEAN_REVERSION', 'direction': 'CE' if direction == 'LONG' else 'PE', 'entry': row['close'], 'sl': sl, 'target': target}

        # 2. MOMENTUM CHECK
        if not best_sig and r_info['allowed']['MOMENTUM']:
            mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
            if mom_sig['signal']:
                score = mom_sig['score']
                conf = min(100, int(score * 12))

                # === VIX FILTER START ===
                # REVERT: Comment out this block to disable VIX filter logic
                adj_conf, allowed, reason = vix_filter.filter_signal(mom_sig['direction'], conf)
                if not allowed:
                    continue
                conf = adj_conf
                # === VIX FILTER END ===

                if conf >= 60:
                    dist = abs(mom_sig['entry'] - mom_sig['sl'])
                    
                    # === PER-STOCK VOLATILITY FILTER START ===
                    # REVERT: Comment out this block to disable wider SL for Momentum
                    if stock_vol == "HIGH_VOL_STOCK":
                        atr = row.get('atr', (df_5m.iloc[i]['High'] - df_5m.iloc[i]['Low']))
                        if mom_sig['direction'] == 'CE':
                            mom_sig['sl'] = min(mom_sig['sl'], mom_sig['entry'] - atr * 1.0)
                        else:
                            mom_sig['sl'] = max(mom_sig['sl'], mom_sig['entry'] + atr * 1.0)
                    # === PER-STOCK VOLATILITY FILTER END ===

                    target = mom_sig['entry'] + (1.5 * dist) if mom_sig['direction'] == 'CE' else mom_sig['entry'] - (1.5 * dist)
                    best_sig = {'strategy': 'MOMENTUM', 'direction': mom_sig['direction'], 'entry': mom_sig['entry'], 'sl': mom_sig['sl'], 'target': target}

        if best_sig:
            entry, sl, target = best_sig['entry'], best_sig['sl'], best_sig['target']
            risk = abs(entry - sl)
            if risk == 0: continue
            
            outcome_r = 0
            found = False
            exit_time = None
            
            # Look-ahead Fix: Exit loop MUST start at i+1
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
                # EOD Exit: Use last bar of the day
                k = i
                while k + 1 < len(df_5m) and df_5m.index[k+1].date() == ts.date():
                    k += 1
                exit_time = df_5m.index[k]
                exit_p = df_5m.iloc[k]['Close']
                
                if exit_time <= ts:
                    outcome_r = 0.0
                    exit_time = ts
                else:
                    outcome_r = (exit_p - entry)/risk if best_sig['direction'] == 'CE' else (entry - exit_p)/risk

            last_exit_ts = exit_time
            trades.append({'ts': ts, 'symbol': symbol, 'r': outcome_r, 'strat': best_sig['strategy'], 'exit_ts': exit_time})
            
    return trades

def main():
    start_dt = datetime(2025, 12, 1)
    end_dt = datetime(2025, 12, 12)

    # === VIX FILTER START ===
    # REVERT: Comment out this block to disable VIX data loading
    print("Loading India VIX data...")
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)
    vix_df.sort_index(inplace=True)
    # === VIX FILTER END ===
    
    nifty_20 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'ITC', 'LT', 'AXISBANK', 'SBIN', 'BHARTIARTL', 'MARUTI', 'BAJFINANCE', 'HCLTECH', 'SUNPHARMA', 'ADANIENT', 'TITAN', 'ULTRACEMCO', 'NTPC', 'JSWSTEEL', 'POWERGRID']
    all_files = [f.split('_')[0] for f in os.listdir('data/angel_historical') if '_1m.csv' in f]
    symbols = nifty_20 + [s for s in all_files if s not in nifty_20][:10]
    
    print(f"REALISTIC GROWTH SIM WITH VIX FILTER: {len(symbols)} stocks...")
    regime_map = get_regime_series(start_dt, end_dt)
    
    args = [(s, start_dt, end_dt, regime_map, vix_df) for s in symbols]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_symbol, args))
    
    all_trades = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    if not all_trades:
        print("No trades found."); return

    equity = INITIAL_CAPITAL
    print("\n--- Compounded Growth Curve (1L Starting Capital) ---")
    current_date = all_trades[0]['ts'].date()
    for t in all_trades:
        if t['ts'].date() > current_date:
            print(f"{current_date}: INR {equity:,.2f}")
            current_date = t['ts'].date()
        
        # Risk 1% of current equity per trade
        risk_amt = equity * 0.01 
        equity += t['r'] * risk_amt

    print(f"{current_date}: INR {equity:,.2f}")
    print(f"\nFINAL CAPITAL ON DEC 12: INR {equity:,.2f}")
    print(f"TOTAL RETURN: {((equity/INITIAL_CAPITAL)-1)*100:.2f}%")

if __name__ == "__main__":
    main()
