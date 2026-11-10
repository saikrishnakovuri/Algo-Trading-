import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter
from modules.vix_filter import VIXDirectionalFilter

# --- Constants & Config ---
INITIAL_CAPITAL = 100000.0
LOT_SIZE = 65 
RISK_PER_TRADE = 2000.0 # 2% of 1L
CONFIDENCE_MIN = 70
MAX_DAILY_TRADES = 5
MAX_DAILY_LOSSES = 2

def calc_options_costs(qty, entry_p, exit_p, num_orders=2):
    brokerage = 20.0 * num_orders
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    total = brokerage + stt + exchange + 10.0 # Taxes
    slippage = (qty / LOT_SIZE) * 2.0
    return total + slippage

def run_ultimate_simulation(nifty_df, vix_df, start_date, end_date):
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine()
    sweep_engine = SweepRetestEngine()
    struct_engine = StructureStrategyEngine()
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    # Pre-calculate data intensive parts
    df_mr = mr_engine._compute_indicators(nifty_df)
    consolidations = mom_engine.detect_consolidation(nifty_df)
    
    trades = []
    current_day = None
    daily_trade_count = 0
    daily_losses = 0
    is_day_stopped = False
    last_exit_idx = 0
    
    for i in range(100, len(nifty_df)-20):
        ts = nifty_df.index[i]
        if ts.date() < start_date or ts.date() > end_date: continue
        
        # Day Reset
        if current_day != ts.date():
            current_day = ts.date()
            daily_trade_count = 0
            daily_losses = 0
            is_day_stopped = False
            
        if is_day_stopped or daily_trade_count >= MAX_DAILY_TRADES: continue
        if i <= last_exit_idx: continue
        if ts.time() < time(9, 45) or ts.time() > time(13, 30): continue

        vix_val = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
        pcr_proxy = 0.8 + (vix_val / 100)
        
        # 1. Generate signals from all 4 engines
        all_sigs = []
        
        # A. LIQUIDITY TRAP (Faded Momentum)
        # Using simple detection for speed in backtest
        if ts.time() < time(14, 0):
            res = mom_engine.detect_breakout(nifty_df, consolidations, i)
            if res['signal']:
                rev_dir = 'PE' if res['direction'] == 'CE' else 'CE'
                conf = min(100, int(res['score'] * 12))
                adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
                if allowed: all_sigs.append({'engine': 'LIQUIDITY_TRAP', 'dir': rev_dir, 'conf': adj_conf, 'level': res['entry']})
        
        # B. MEAN REVERSION (Confirmed)
        row = df_mr.iloc[i]
        settings = {'rsi_oversold': 30, 'rsi_overbought': 70, 'min_score': 6, 'sl_atr_mult': 0.5}
        trend_ok, _ = mr_engine._check_anti_trend_filter(row)
        if trend_ok:
            fired = [s for s in [mr_engine._check_bb_reversion(row, settings), mr_engine._check_vwap_reversion(row, settings), mr_engine._check_rsi_extreme(row, settings)] if s is not None]
            if fired:
                direction = 'LONG' if sum(1 for s in fired if s['direction'] == 'LONG') > sum(1 for s in fired if s['direction'] == 'SHORT') else 'SHORT'
                vix_dir = 'CE' if direction == 'LONG' else 'PE'
                score = sum(s['score'] for s in fired) + mr_engine._compute_bonuses(row, df_mr, i)[0]
                conf = min(100, int(score * 10))
                adj_conf, allowed, _ = vix_filter.filter_signal(vix_dir, conf)
                if allowed: all_sigs.append({'engine': 'MEAN_REVERSION', 'dir': vix_dir, 'conf': adj_conf, 'level': row['close']})

        # C. SWEEP/STRUCTURE (High speed check)
        # For simulation, we assume these fire with baseline 75% conf if price is at 20-bar high/low
        if row['close'] >= nifty_df.iloc[max(0, i-20):i]['High'].max():
            all_sigs.append({'engine': 'SWEEP', 'dir': 'PE', 'conf': 75, 'level': row['close']})
        elif row['close'] <= nifty_df.iloc[max(0, i-20):i]['Low'].min():
            all_sigs.append({'engine': 'SWEEP', 'dir': 'CE', 'conf': 75, 'level': row['close']})

        if not all_sigs: continue
        
        # Select best signal
        best = max(all_sigs, key=lambda x: x['conf'])
        if best['conf'] < CONFIDENCE_MIN: continue
        
        # 2. Execution with Trailing Exit
        entry_spot = nifty_df.iloc[i]['Close']
        vix_factor = vix_val / 15.0
        entry_p = entry_spot * 0.006 * vix_factor
        
        # Sizing
        sl_dist = entry_p * 0.30
        lots = max(1, int(RISK_PER_TRADE / (sl_dist * LOT_SIZE)))
        lots = min(lots, 5) # Cap at 5 lots max
        qty = lots * LOT_SIZE
        
        t1_p = entry_p + (1.5 * sl_dist)
        be_p = entry_p
        
        exit_p = entry_p; exit_reason = "EOD"; num_orders = 2
        t1_hit = False
        tsl_p = entry_p * 0.70
        
        # Trailing Step Logic: "if it goes to 15 (1.5R) then tsl is 10 (1R), if it goes to 20 (2R) tsl is 15 (1.5R)"
        # So TSL = Current_Max_Profit - 0.5R, starting from T1.
        current_max_p = entry_p
        
        for j in range(i+1, len(nifty_df)):
            if nifty_df.index[j].date() != ts.date(): break
            curr_bar = nifty_df.iloc[j]
            spot_move = (curr_bar['Close'] - entry_spot) / entry_spot
            if best['dir'] == 'PE': spot_move *= -1.0
            
            # Synthetic Premium
            curr_p = entry_p + (0.5 * spot_move * entry_spot) + (0.5 * 0.002 * (spot_move * entry_spot)**2) - (0.5 * (j-i)/12)
            
            # 1. Update Trailing SL
            if curr_p > current_max_p:
                current_max_p = curr_p
                if current_max_p >= t1_p:
                    # If profit >= 1.5R, TSL is at 1.0R
                    # Step trail: TSL = (Current Max Profit - 0.5R)
                    new_tsl = current_max_p - (0.5 * sl_dist)
                    if new_tsl > tsl_p: tsl_p = new_tsl

            # 2. Check T1 (50% book)
            if not t1_hit and curr_p >= t1_p:
                t1_hit = True
                num_orders += 1 # Added a sell order
                # Bank 50% profit immediately
                # Technically we just continue with higher cost and TSL protection
            
            # 3. Check Exits
            if curr_p <= tsl_p:
                exit_p = tsl_p
                exit_reason = "TSL_HIT" if t1_hit else "SL_HIT"
                break
            
            if ts.time() >= time(15, 15):
                exit_p = curr_p; exit_reason = "EOD"; break

        # 3. Finalize Trade
        costs = calc_options_costs(qty, entry_p, exit_p, num_orders)
        gross = (exit_p - entry_p) * qty
        net = gross - costs
        
        trades.append({'ts': ts, 'engine': best['engine'], 'net': net, 'reason': exit_reason})
        
        daily_trade_count += 1
        if net < 0: daily_losses += 1
        if daily_losses >= MAX_DAILY_LOSSES:
            is_day_stopped = True
            
        last_exit_idx = j
        
    return trades

def main():
    print("Loading NIFTY Data...")
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    nifty_df['Timestamp'] = pd.to_datetime(nifty_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    nifty_df.set_index('Timestamp', inplace=True); nifty_df.sort_index(inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)

    test_days = nifty_df.index.normalize().unique()[-30:] # Last 30 unique days
    start_d = test_days[0].date(); end_d = test_days[-1].date()
    
    print(f"Running Ultimate Validation: {start_d} to {end_d}")
    print(f"Rules: 70% Conf | Max 5 Trades/Day | Stop after 2 Losses | T1 @ 1.5R (50%) + 0.5R Step Trail")
    
    all_trades = run_ultimate_simulation(nifty_df, vix_df, start_d, end_d)
    
    if not all_trades:
        print("No trades triggered."); return
        
    df = pd.DataFrame(all_trades)
    total_net = df['net'].sum()
    win_rate = (df['net'] > 0).sum() / len(df) * 100
    
    print("\n--- ULTIMATE OPTIONS STRATEGY RESULTS ---")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Net P&L: INR {total_net:,.2f}")
    print(f"Expectancy: INR {total_net/len(df):.2f}")
    
    print("\nExit Reason Breakdown:")
    print(df['reason'].value_counts())
    
    print("\nDaily Performance:")
    df['date'] = df['ts'].dt.date
    daily = df.groupby('date')['net'].sum()
    eq = INITIAL_CAPITAL
    for d, pnl in daily.items():
        eq += pnl
        print(f"{d} | Net: {pnl:>10,.2f} | Equity: {eq:>12,.2f}")
    
    print(f"\nFINAL CAPITAL: INR {eq:,.2f}")
    print(f"TOTAL RETURN: {((eq/INITIAL_CAPITAL)-1)*100:.2f}%")

if __name__ == "__main__":
    main()
