import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine

LOT_SIZE = 65  # Nifty lot size from 2026
RISK_PER_TRADE = 20000.0
MAX_LOTS = 5
INITIAL_CAPITAL = 1000000.0

def calc_options_costs(qty, entry_p, exit_p):
    buy_turnover = qty * entry_p
    sell_turnover = qty * exit_p
    brokerage = 40.0 
    stt = 0.000625 * sell_turnover 
    exchange = 0.0005 * (buy_turnover + sell_turnover)
    gst = 0.18 * 40.0
    sebi = 0.000001 * (buy_turnover + sell_turnover)
    stamp = 0.00003 * buy_turnover
    total_costs = brokerage + stt + exchange + gst + sebi + stamp
    slippage = (qty / LOT_SIZE) * 2.0 # ₹2 per lot round trip
    return total_costs + slippage

def get_signals(nifty_df, vix_df, mode):
    signals = []
    
    # Calculate ATR once for speed
    high = nifty_df['High']
    low = nifty_df['Low']
    close = nifty_df['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr_series = tr.rolling(14).mean()

    rolling_high = nifty_df['High'].rolling(20).max()
    rolling_low = nifty_df['Low'].rolling(20).min()
    
    for i in range(100, len(nifty_df)-20):
        ts = nifty_df.index[i]
        curr_time = ts.time()
        
        # Time Gate: 09:45 to 14:00
        if curr_time < time(9, 45) or curr_time >= time(14, 0):
            continue
            
        vix_val = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
        pcr_val = 0.8 + (vix_val / 100)
        
        # Find consolidations manually for speed/simplicity
        range_val = rolling_high.iloc[i-1] - rolling_low.iloc[i-1]
        atr_val = atr_series.iloc[i-1]
        
        consols = []
        if range_val < (atr_val * 3.5):
            consols.append({
                'high': rolling_high.iloc[i-1],
                'low': rolling_low.iloc[i-1],
                'end_idx': i - 1,
                'volume_avg': 1.0
            })
            
        if not consols: continue
        
        curr = nifty_df.iloc[i]
        candle_range = curr['High'] - curr['Low']
        
        mom_dir = None
        level_swept = 0
        if curr['Close'] > consols[0]['high'] and candle_range > (atr_val * 1.2):
            mom_dir = 'CE'
            level_swept = consols[0]['high']
        elif curr['Close'] < consols[0]['low'] and candle_range > (atr_val * 1.2):
            mom_dir = 'PE'
            level_swept = consols[0]['low']
            
        if not mom_dir: continue
        
        # Base confidence
        base_confidence = 70 
        
        if mode == "FADE":
            options_dir = 'PE' if mom_dir == 'CE' else 'CE'
        else: # FOLLOW
            options_dir = 'CE' if mom_dir == 'CE' else 'PE'
            
        # VIX Filter
        if vix_val > 20.0:
            if mode == "FADE":
                if options_dir == 'CE': continue
                else: base_confidence += 15
            else: # FOLLOW
                if options_dir == 'CE': base_confidence -= 15
                else: base_confidence += 15
        elif 14.0 <= vix_val <= 20.0:
            base_confidence -= 5
            
        # PCR Filter
        if pcr_val > 1.3:
            if options_dir == 'CE': base_confidence -= 15
            else: base_confidence += 10
        elif pcr_val < 0.7:
            if options_dir == 'PE': base_confidence -= 15
            else: base_confidence += 10
            
        # VWAP Gravity (Mocked since no volume)
        df_today = nifty_df[nifty_df.index.date == ts.date()].copy()
        df_today['cum_vol_price'] = (df_today['Close'] * 1).cumsum() 
        df_today['cum_vol'] = np.arange(1, len(df_today)+1)
        vwap = df_today['cum_vol_price'].iloc[-1] / df_today['cum_vol'].iloc[-1]
        
        if mode == "FADE":
            if options_dir == 'PE' and curr['Close'] > vwap: base_confidence += 10
            elif options_dir == 'CE' and curr['Close'] < vwap: base_confidence += 10
            else: base_confidence -= 15
        else: # FOLLOW
            if options_dir == 'CE' and curr['Close'] > vwap: base_confidence += 10
            elif options_dir == 'PE' and curr['Close'] < vwap: base_confidence += 10
            else: base_confidence -= 15
            
        # Psychological Strike
        nearest_strike = int(round(curr['Close'] / 50) * 50)
        if nearest_strike % 100 == 0 and abs(curr['Close'] - nearest_strike)/nearest_strike <= 0.001:
            base_confidence += 15
            
        final_confidence = min(100, max(0, base_confidence))
        
        # Lowered to 65% threshold for statistics
        if final_confidence >= 65:
            signals.append({
                'idx': i,
                'timestamp': ts,
                'options_direction': options_dir,
                'spot_price': curr['Close'],
                'level_swept': level_swept,
                'confidence': final_confidence,
                'vix': vix_val
            })
            
    return signals

def simulate_synthetic_option(df_5m, signal):
    entry_idx = signal['idx']
    entry_spot = signal['spot_price']
    entry_ts = signal['timestamp']
    direction = signal['options_direction']
    
    vix_factor = signal['vix'] / 15.0
    entry_premium = entry_spot * 0.006 * vix_factor
    
    # Position Sizing FIX (lots calculation)
    lots = max(1, int(RISK_PER_TRADE / (entry_premium * LOT_SIZE)))
    lots = min(lots, MAX_LOTS)
    qty = lots * LOT_SIZE
    
    current_premium = entry_premium
    exit_p = entry_premium
    exit_reason = "EOD"
    
    target_p = entry_premium * 1.50
    sl_p = entry_premium * 0.70
    max_duration = 90
    
    for j in range(entry_idx + 1, len(df_5m)):
        curr_bar = df_5m.iloc[j]
        ts = df_5m.index[j]
        if ts.date() != entry_ts.date(): break
        
        spot_move_pct = (curr_bar['Close'] - entry_spot) / entry_spot
        if direction == 'PE': spot_move_pct *= -1.0
        
        delta_effect = 0.50 * spot_move_pct * entry_spot
        gamma_effect = 0.5 * 0.002 * (spot_move_pct * entry_spot)**2
        elapsed_hours = (ts - entry_ts).total_seconds() / 3600
        theta_effect = -3.0 * elapsed_hours
        
        current_premium = entry_premium + delta_effect + gamma_effect + theta_effect
        
        if ts.time() >= time(15, 15):
            exit_p = current_premium; exit_reason = "EOD"; break
        if (ts - entry_ts).total_seconds() / 60 > max_duration:
            exit_p = current_premium; exit_reason = f"TIME_{max_duration}"; break
        if current_premium >= target_p:
            exit_p = target_p; exit_reason = "TARGET"; break
        if current_premium <= sl_p:
            exit_p = sl_p; exit_reason = "STOP_LOSS"; break
        struct_hit = (curr_bar['Close'] > signal['level_swept']) if direction == 'PE' else (curr_bar['Close'] < signal['level_swept'])
        if struct_hit:
            exit_p = current_premium; exit_reason = "STRUCTURAL_SL"; break

    costs = calc_options_costs(qty, entry_premium, exit_p)
    net_pnl = (exit_p - entry_premium) * qty - costs
    
    return {
        'net_pnl': net_pnl,
        'gross_pnl': (exit_p - entry_premium) * qty,
        'costs': costs,
        'reason': exit_reason,
        'date': entry_ts.date(),
        'idx': entry_idx,
        'exit_idx': j
    }

def run_test(df, vix_df, mode):
    print(f"Running {mode} Test (65% Threshold)...")
    signals = get_signals(df, vix_df, mode)
    print(f"{mode} Signals detected: {len(signals)}")
    
    results = []
    last_exit_idx = 0
    for s in signals:
        if s['idx'] <= last_exit_idx: continue # Position lock
        
        res = simulate_synthetic_option(df, s)
        results.append(res)
        last_exit_idx = res['exit_idx']
        
    return results

def main():
    print("Loading NIFTY Data...")
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    nifty_df.set_index('Timestamp', inplace=True); nifty_df.sort_index(inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    fade_res = run_test(nifty_df, vix_df, "FADE")
    follow_res = run_test(nifty_df, vix_df, "FOLLOW")
    
    def summarize(res):
        if not res: return 0, 0, 0, 0
        trades = len(res)
        wins = sum(1 for r in res if r['net_pnl'] > 0)
        net = sum(r['net_pnl'] for r in res)
        # Max DD calculation
        eq = INITIAL_CAPITAL
        eq_curve = [eq]
        for r in res:
            eq += r['net_pnl']
            eq_curve.append(eq)
        peak = INITIAL_CAPITAL
        max_dd = 0
        for val in eq_curve:
            if val > peak: peak = val
            dd = (peak - val) / peak * 100
            if dd > max_dd: max_dd = dd
        return trades, (wins/trades)*100, net, max_dd

    f_tr, f_wr, f_net, f_dd = summarize(fade_res)
    fl_tr, fl_wr, fl_net, fl_dd = summarize(follow_res)
    
    print("\n--- FINAL COMPARISON: FADE VS FOLLOW (6 Months) ---")
    print("| Metric | FADE (Test A) | FOLLOW (Test B) |")
    print("|--------|--------------|-----------------|")
    print(f"| Trades | {f_tr} | {fl_tr} |")
    print(f"| Win Rate | {f_wr:.1f}% | {fl_wr:.1f}% |")
    print(f"| Net P&L | INR {f_net:,.2f} | INR {fl_net:,.2f} |")
    print(f"| Max DD | {f_dd:.1f}% | {fl_dd:.1f}% |")

if __name__ == '__main__':
    main()
