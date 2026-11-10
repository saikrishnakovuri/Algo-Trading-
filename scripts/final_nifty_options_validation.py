import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time

# Final Config for 1 Lakh Capital
CAPITAL = 100000.0
LOT_SIZE = 65 
RISK_PER_TRADE = 2000.0 # 2% risk
MAX_LOTS = 1 # Strictly 1 lot for 1L capital safety

def calc_options_costs(qty, entry_p, exit_p):
    brokerage = 40.0 # 20 per side
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    total = brokerage + stt + exchange + 10.0 # + GST/Stamp
    slippage = (qty / LOT_SIZE) * 2.0 # ₹2 per lot
    return total + slippage

def run_nifty_options_validation(set_name, start_date, end_date, nifty_df, vix_df):
    results = []
    last_exit_idx = 0
    
    # Pre-calculate ATR for signals
    high = nifty_df['High']; low = nifty_df['Low']; close = nifty_df['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr_series = tr.rolling(14).mean()
    rolling_high = nifty_df['High'].rolling(20).max()
    rolling_low = nifty_df['Low'].rolling(20).min()

    for i in range(100, len(nifty_df)-20):
        ts = nifty_df.index[i]
        if ts.date() < start_date or ts.date() > end_date: continue
        if i <= last_exit_idx: continue
        if ts.time() < time(9, 45) or ts.time() > time(13, 30): continue

        vix = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
        atr = atr_series.iloc[i-1]
        
        # Signal: Liquidity Trap (Price Action)
        r_high = rolling_high.iloc[i-1]
        r_low = rolling_low.iloc[i-1]
        curr = nifty_df.iloc[i]
        
        # 75% Confidence Filter
        sig_dir = None
        if curr['Close'] > r_high and (curr['High'] - curr['Low']) > (atr * 1.2): sig_dir = 'PE' # Fade up
        elif curr['Close'] < r_low and (curr['High'] - curr['Low']) > (atr * 1.2): sig_dir = 'CE' # Fade down
        
        if sig_dir:
            # 1. Entry Premium & Risk
            entry_spot = curr['Close']
            entry_p = entry_spot * 0.006 * (vix/15.0)
            
            # 2. Position Sizing
            sl_points = entry_p * 0.30
            lots = max(1, int(RISK_PER_TRADE / (sl_points * LOT_SIZE)))
            lots = min(lots, MAX_LOTS)
            qty = lots * LOT_SIZE
            
            # 3. Simulate Option Outcome
            target_p = entry_p * 1.50
            be_trigger_p = entry_p * 1.35
            sl_p = entry_p * 0.70
            
            exit_p = entry_p; reason = "EOD"; be_active = False
            for j in range(i+1, min(i+20, len(nifty_df))):
                curr_bar = nifty_df.iloc[j]
                spot_move = (curr_bar['Close'] - entry_spot) / entry_spot
                if sig_dir == 'PE': spot_move *= -1.0
                
                # Synthetic Premium
                curr_p = entry_p + (0.5 * spot_move * entry_spot) + (0.5 * 0.002 * (spot_move * entry_spot)**2) - (0.5 * (j-i)/12)
                
                if not be_active and curr_p >= be_trigger_p: be_active = True; sl_p = entry_p
                if curr_p >= target_p: exit_p = target_p; reason = "TARGET"; break
                if curr_p <= sl_p: exit_p = sl_p; reason = "STOP_LOSS"; break
            
            costs = calc_options_costs(qty, entry_p, exit_p)
            net = ((exit_p - entry_p) * qty) - costs
            results.append({'date': ts.date(), 'net': net, 'reason': reason, 'lots': lots, 'risk': sl_points * qty})
            last_exit_idx = j
            
    return results

def main():
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    nifty_df.set_index('Timestamp', inplace=True); nifty_df.sort_index(inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)

    sets = [
        ("SET 1: Dec Crash", datetime(2025, 12, 1).date(), datetime(2025, 12, 20).date()),
        ("SET 2: Jan Trend", datetime(2026, 1, 8).date(), datetime(2026, 2, 7).date()),
        ("SET 3: Feb/Mar Mix", datetime(2026, 2, 20).date(), datetime(2026, 3, 20).date())
    ]
    
    print(f"--- NIFTY OPTIONS 3-SET VALIDATION (CAPITAL: INR {CAPITAL:,.0f}) ---")
    total_net = 0
    for name, start, end in sets:
        res = run_nifty_options_validation(name, start, end, nifty_df, vix_df)
        net = sum(r['net'] for r in res)
        wr = sum(1 for r in res if r['net'] > 0) / len(res) * 100 if res else 0
        total_net += net
        print(f"{name:<20} | Trades: {len(res):<3} | WinRate: {wr:>5.1f}% | Net P&L: INR {net:>8,.2f}")

    print("-" * 65)
    print(f"FINAL CONSOLIDATED P&L: INR {total_net:,.2f}")
    print(f"TOTAL RETURN ON 1L: {total_net/CAPITAL*100:.2f}%")

if __name__ == "__main__":
    main()
