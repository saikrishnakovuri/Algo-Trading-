import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.options.risk_manager import OptionsRiskManager

# --- Constants & Config ---
INITIAL_CAPITAL = 1000000.0
LOT_SIZE = 25 # NIFTY
RISK_PER_TRADE = 20000.0 # 2% of 10L

def calc_options_costs(qty, entry_p, exit_p):
    """Precise Option Brokerage & Tax Formula."""
    buy_turnover = qty * entry_p
    sell_turnover = qty * exit_p
    
    brokerage = 40.0 # 20 per side
    stt = 0.000625 * sell_turnover # 0.0625% on sell side premium
    exchange = 0.0005 * (buy_turnover + sell_turnover) # 0.05% on total premium
    gst = 0.18 * 40.0
    sebi = 0.000001 * (buy_turnover + sell_turnover)
    stamp = 0.00003 * buy_turnover
    
    total_costs = brokerage + stt + exchange + gst + sebi + stamp
    # Add Slippage: ₹2 per lot round trip
    slippage = (qty / LOT_SIZE) * 2.0
    return total_costs + slippage

def simulate_synthetic_option(df_5m, signal, vix_df):
    """
    Estimates ATM premium movement using Delta-Gamma-Theta-Vega approximations.
    """
    entry_idx = signal['idx']
    entry_spot = signal['spot_price']
    entry_ts = signal['timestamp']
    direction = signal['options_direction']
    
    # Adjusted by VIX
    vix_factor = signal['vix'] / 15.0
    entry_premium = entry_spot * 0.006 * vix_factor
    
    qty = int(RISK_PER_TRADE / entry_premium)
    if qty < 1: qty = 1
    
    current_premium = entry_premium
    exit_p = entry_premium
    exit_reason = "EOD"
    exit_time = entry_ts
    
    # Exit Rules
    target_p = entry_premium * 1.50
    sl_p = entry_premium * 0.70
    
    max_duration = 45 if signal.get('is_expiry', False) else 90
    
    for j in range(entry_idx + 1, len(df_5m)):
        curr_bar = df_5m.iloc[j]
        ts = df_5m.index[j]
        if ts.date() != entry_ts.date(): break
        
        # 1. Underlying Move
        spot_move_pct = (curr_bar['Close'] - entry_spot) / entry_spot
        if direction == 'PE': spot_move_pct *= -1.0 # Reverse for Puts
        
        # 2. Delta-Gamma Premium Change
        delta_effect = 0.50 * spot_move_pct * entry_spot
        gamma_effect = 0.5 * 0.002 * (spot_move_pct * entry_spot)**2
        
        # 3. Theta Decay (₹3 per hour approx)
        elapsed_hours = (ts - entry_ts).total_seconds() / 3600
        theta_effect = -3.0 * elapsed_hours
        
        current_premium = entry_premium + delta_effect + gamma_effect + theta_effect
        
        # 4. Monitor Exits
        if ts.time() >= time(15, 15):
            exit_p = current_premium; exit_time = ts; exit_reason = "EOD"; break
            
        if (ts - entry_ts).total_seconds() / 60 > max_duration:
            exit_p = current_premium; exit_time = ts; exit_reason = f"TIME_{max_duration}"; break
            
        if current_premium >= target_p:
            exit_p = target_p; exit_time = ts; exit_reason = "TARGET"; break
        if current_premium <= sl_p:
            exit_p = sl_p; exit_time = ts; exit_reason = "STOP_LOSS"; break
            
        struct_hit = (curr_bar['Close'] > signal['level_swept']) if direction == 'PE' else (curr_bar['Close'] < signal['level_swept'])
        if struct_hit:
            exit_p = current_premium; exit_time = ts; exit_reason = "STRUCTURAL_SL"; break

    net_pnl = (exit_p - entry_premium) * qty * LOT_SIZE
    costs = calc_options_costs(qty * LOT_SIZE, entry_premium, exit_p)
    
    return {
        'date': entry_ts.date(),
        'dir': direction,
        'entry': round(entry_premium, 2),
        'exit': round(exit_p, 2),
        'exit_time': exit_time,
        'reason': exit_reason,
        'gross': round(net_pnl + costs, 2),
        'costs': round(costs, 2),
        'net': round(net_pnl, 2)
    }

def main():
    print("Initializing Phase 5: Options Backtest Engine...")
    
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    nifty_df.set_index('Timestamp', inplace=True); nifty_df.sort_index(inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    adapter = IndexLiquidityTrapAdapter()
    risk_mgr = OptionsRiskManager(INITIAL_CAPITAL)
    
    signals_processed = 0
    trades_taken = 0
    last_exit_bar = 0
    current_day = None
    
    mock_oi = {i: {'ce_oi': 2000000, 'pe_oi': 2000000, 'ce_oi_change': 0, 'pe_oi_change': 0} for i in range(15000, 30000, 50)}

    results = []
    print("Scanning for signals across 6 months...")

    for i in range(100, len(nifty_df)-20):
        ts = nifty_df.index[i]
        
        if current_day != ts.date():
            risk_mgr.daily_reset()
            if ts.weekday() == 0: risk_mgr.weekly_reset()
            current_day = ts.date()

        if i <= last_exit_bar: continue

        can_trade, reason = risk_mgr.can_trade("NIFTY", ts)
        if not can_trade: continue

        vix_val = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
        pcr_proxy = 0.8 + (vix_val / 100)
        
        sig = adapter.evaluate_signal(nifty_df.iloc[:i+1], "NIFTY", vix_val, pcr_proxy, mock_oi, False)
        
        if sig and sig['confidence'] >= 75:
            signals_processed += 1
            sig['idx'] = i
            res = simulate_synthetic_option(nifty_df, sig, vix_df)
            risk_mgr.record_trade(res['net'], ts)
            
            duration_sec = (res['exit_time'] - ts).total_seconds()
            bars_held = int(duration_sec / 300)
            last_exit_bar = i + bars_held
            
            res['confidence'] = sig['confidence']
            results.append(res)
            trades_taken += 1

    if not results:
        print("No signals matched execution criteria. Backtest finished with zero trades.")
        return

    df_results = pd.DataFrame(results)
    
    print("\n--- OPTIONS BACKTEST SUMMARY (Oct 2025 - Apr 2026) ---")
    print(f"Total Signals Detected: {signals_processed}")
    print(f"Trades Taken (Risk Approved): {trades_taken}")
    
    # Exit Breakdown
    print("\nExit Type Breakdown:")
    print(df_results['reason'].value_counts())

    df_results['month'] = pd.to_datetime(df_results['date']).dt.strftime('%Y-%m')
    monthly = df_results.groupby('month').agg({'net': 'sum', 'entry': 'count'}).rename(columns={'entry': 'trades', 'net': 'net_pnl'})
    print("\nMonthly P&L:")
    print(monthly)
    
    total_net = df_results['net'].sum()
    total_costs = df_results['costs'].sum()
    win_rate = (df_results['net'] > 0).sum() / len(df_results) * 100
    avg_net = total_net / len(df_results)
    
    print(f"\n| Metric | Value |")
    print("| :--- | :--- |")
    print(f"| Total Trades | {len(df_results)} |")
    print(f"| Win Rate | {win_rate:.1f}% |")
    print(f"| Total Gross P&L | INR {total_net + total_costs:,.2f} |")
    print(f"| Total Costs (Taxes) | INR {total_costs:,.2f} |")
    print(f"| **Final Net P&L** | **INR {total_net:,.2f}** |")
    print(f"| Net Expectancy/Trade | INR {avg_net:,.2f} |")
    print(f"| Profit Factor | {(df_results[df_results['net']>0]['net'].sum() / abs(df_results[df_results['net']<0]['net'].sum())):.2f} |")

if __name__ == "__main__":
    main()
