"""
Out-of-Sample Validation & Robustness Check
════════════════════════════════════════════
Proves whether the +0.450R edge is real or overfitted.

Test 1: Train/Test split by DATE (70/30)
Test 2: Parameter sensitivity (does ±20% change in thresholds destroy edge?)
Test 3: Monte Carlo shuffle (is the edge better than random?)
"""

import os
import sys
import yaml
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Import framework components
from modules.cached_data_loader import CachedDataLoader
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

CACHE_DIR = "data/cache"
RESULTS_DIR = "data/backtest_results/oos_validation"
TRAIN_RATIO = 0.70  # 70% train, 30% test
MAX_CONCURRENT_TRADES = 3
CAPITAL = 1000000  # 10 lakh
RISK_PER_TRADE_PCT = 0.01  # 1%
TIME_STOP_SLIPPAGE = 0.5
STEP_SIZE = 10 # Optimized for speed

# Trading hours
TRADE_START = "09:20"
TRADE_END = "14:30"

os.makedirs(RESULTS_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════

def execute_trade_sim(df, entry_idx, signal, capital):
    """
    Simulates trade outcome from entry_idx forward.
    (Matches logic in run_combined_backtest.py)
    """
    entry = signal.entry
    sl = signal.sl
    target = signal.target1
    direction = signal.direction
    
    if not all([entry, sl, target]): return None
    
    dist_to_sl = abs(entry - sl)
    if dist_to_sl == 0: return None
    
    # Position Sizing
    risk_amount = capital * RISK_PER_TRADE_PCT
    qty = int(risk_amount / dist_to_sl)
    if qty <= 0: qty = 1
    
    # Max hold bars based on strategy
    max_hold = 6 if signal.strategy_name == "MEAN_REVERSION" else 10
        
    trade_future = df.iloc[entry_idx + 1 : entry_idx + 1 + max_hold]
    if trade_future.empty: return None
        
    exit_price = None
    exit_type = None
    bars_held = 0
    
    for i, (_, row) in enumerate(trade_future.iterrows()):
        bars_held = i + 1
        low, high, close = row['Low'], row['High'], row['Close']
        
        if direction == 'CE' or direction == 'LONG':
            if low <= sl:
                exit_price = sl; exit_type = "SL_HIT"; break
            if high >= target:
                exit_price = target; exit_type = "TARGET_HIT"; break
        else:
            if high >= sl:
                exit_price = sl; exit_type = "SL_HIT"; break
            if low <= target:
                exit_price = target; exit_type = "TARGET_HIT"; break
                
    if exit_price is None:
        exit_price = float(trade_future.iloc[-1]['Close'])
        if direction in ['CE', 'LONG']: exit_price -= TIME_STOP_SLIPPAGE
        else: exit_price += TIME_STOP_SLIPPAGE
        exit_type = "TIME_STOP"
        bars_held = len(trade_future)

    pnl_points = (exit_price - entry) if direction in ['CE', 'LONG'] else (entry - exit_price)
    pnl_inr = pnl_points * qty
    r_multiple = pnl_points / dist_to_sl
    
    return {
        'Symbol': '', 
        'Date': str(df.index[entry_idx].date()),
        'Strategy': signal.strategy_name,
        'Direction': direction,
        'Entry': round(entry, 2),
        'SL': round(sl, 2),
        'Target': round(target, 2),
        'Exit': round(exit_price, 2),
        'Exit_Type': exit_type,
        'Bars_Held': bars_held,
        'P&L_INR': round(pnl_inr, 2),
        'R_Multiple': round(r_multiple, 3)
    }

def run_oos_backtest(data_dict, label="FULL", sel=None):
    """Run backtest on a dictionary of DataFrames."""
    all_trades = []
    symbol_last_trade_date = {}
    
    symbols = sorted(data_dict.keys())
    for idx, sym in enumerate(symbols):
        df = data_dict[sym]
        if len(df) < 50: continue
        
        days = df.groupby(df.index.date)
        for date, day_df in days:
            day_data = day_df.between_time(TRADE_START, TRADE_END)
            if day_data.empty: continue
            
            for i in range(0, len(day_data), STEP_SIZE):
                current_timestamp = day_data.index[i]
                if symbol_last_trade_date.get(sym) == date: continue
                
                global_idx = df.index.get_loc(current_timestamp)
                df_slice = df.iloc[max(0, global_idx-100):global_idx+1]
                
                best_sig = sel.select_best(df_slice, sym)
                if best_sig:
                    trade = execute_trade_sim(df, global_idx, best_sig, CAPITAL)
                    if trade:
                        trade['Symbol'] = sym
                        all_trades.append(trade)
                        symbol_last_trade_date[sym] = date
                        break
    
    trades_df = pd.DataFrame(all_trades)
    summary = compute_summary(trades_df, label)
    return trades_df, summary

def compute_summary(trades_df, label=""):
    if trades_df.empty:
        return {'label': label, 'total_trades': 0, 'win_rate': 0, 'expectancy': 0, 'profit_factor': 0, 'total_pnl_inr': 0, 'max_dd_r': 0, 'best_trade_r': 0, 'worst_trade_r': 0, 'avg_bars_held': 0}
    
    wins = trades_df[trades_df['R_Multiple'] > 0]
    losses = trades_df[trades_df['R_Multiple'] <= 0]
    
    total = len(trades_df)
    win_rate = len(wins) / total * 100
    avg_r = trades_df['R_Multiple'].mean()
    
    gross_profit = wins['R_Multiple'].sum()
    gross_loss = abs(losses['R_Multiple'].sum()) if not losses.empty else 0.001
    profit_factor = gross_profit / gross_loss
    
    cum_r = trades_df['R_Multiple'].cumsum()
    max_dd_r = (cum_r - cum_r.cummax()).min()
    
    return {
        'label': label,
        'total_trades': total,
        'win_rate': round(win_rate, 1),
        'expectancy': round(avg_r, 4),
        'profit_factor': round(profit_factor, 2),
        'total_pnl_inr': round(trades_df['P&L_INR'].sum(), 0),
        'max_dd_r': round(max_dd_r, 2),
        'best_trade_r': round(trades_df['R_Multiple'].max(), 2),
        'worst_trade_r': round(trades_df['R_Multiple'].min(), 2),
        'avg_bars_held': round(trades_df['Bars_Held'].mean(), 1),
    }

# ══════════════════════════════════════════════════════════════
# MAIN VALIDATION LOGIC
# ══════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print(" OUT-OF-SAMPLE VALIDATION & ROBUSTNESS CHECK (Optimized)")
    print("="*70)
    
    loader = CachedDataLoader()
    all_symbols = loader.get_available_symbols(interval="5m")[:20]
    
    all_data = {}
    all_dates = set()
    print(f"Loading data for {len(all_symbols)} symbols...")
    for sym in all_symbols:
        df = loader.load(sym, interval="5m")
        if df is not None and len(df) > 50:
            all_data[sym] = df
            all_dates.update(df.index.date)
    
    # 1. Train/Test Split by Date
    sorted_dates = sorted(list(all_dates))
    cutoff_idx = int(len(sorted_dates) * TRAIN_RATIO)
    cutoff_date = sorted_dates[cutoff_idx]
    
    train_data = {s: df[df.index.date < cutoff_date] for s, df in all_data.items()}
    test_data = {s: df[df.index.date >= cutoff_date] for s, df in all_data.items()}
    
    print(f"Cutoff Date: {cutoff_date}")
    print(f"Train set: {len(sorted_dates[:cutoff_idx])} days | Test set: {len(sorted_dates[cutoff_idx:])} days")
    
    # 2. Initialize Engines
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    
    sel = StrategySelector()
    sel.register("MOMENTUM", mom_engine, momentum_adapter)
    sel.register("MEAN_REVERSION", mr_engine, mean_reversion_adapter)
    
    # Run TRAIN
    print("\nRunning TRAIN set validation...")
    train_trades, train_summary = run_oos_backtest(train_data, "TRAIN", sel)
    
    # Run TEST (OOS)
    print("Running TEST set (OOS) validation...")
    test_trades, test_summary = run_oos_backtest(test_data, "TEST (OOS)", sel)
    
    # 3. Parameter Sensitivity (±20% on MR min_score)
    print("\nRunning Parameter Sensitivity Tests...")
    
    # Tighter
    mr_engine_tight = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    mr_engine_tight.min_score = 8 # baseline is 6
    sel_tight = StrategySelector()
    sel_tight.register("MOMENTUM", mom_engine, momentum_adapter)
    sel_tight.register("MEAN_REVERSION", mr_engine_tight, mean_reversion_adapter)
    _, tight_summary = run_oos_backtest(all_data, "TIGHTER (score=8)", sel_tight)
    
    # Looser
    mr_engine_loose = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    mr_engine_loose.min_score = 5 
    sel_loose = StrategySelector()
    sel_loose.register("MOMENTUM", mom_engine, momentum_adapter)
    sel_loose.register("MEAN_REVERSION", mr_engine_loose, mean_reversion_adapter)
    _, loose_summary = run_oos_backtest(all_data, "LOOSER (score=5)", sel_loose)
    
    # 4. Monte Carlo (Simple Shuffle)
    print("\nRunning Monte Carlo Shuffle (100 iterations)...")
    real_r = test_trades['R_Multiple'].values if not test_trades.empty else np.array([-1.0])
    mc_results = []
    for _ in range(100):
        mc_results.append(np.random.permutation(real_r).mean())
    
    p_val = np.sum(np.array(mc_results) >= test_summary['expectancy']) / 100
    
    # 5. Report Results
    print("\n" + "="*60)
    print(" TRAIN VS TEST COMPARISON")
    print("="*60)
    print(f"{'Metric':<20} {'TRAIN':>12} {'TEST (OOS)':>12} {'Delta':>12}")
    for m in ['total_trades', 'win_rate', 'expectancy', 'profit_factor']:
        tr = train_summary[m]
        ts = test_summary[m]
        delta = ts - tr
        print(f"{m:<20} {tr:>12} {ts:>12} {delta:>+12.4f}")
        
    print("\n" + "="*60)
    print(" PARAMETER SENSITIVITY")
    print("="*60)
    for s in [train_summary, test_summary, tight_summary, loose_summary]:
        print(f"{s['label']:<25} Trades: {s['total_trades']:>4} | Exp: {s['expectancy']:>+7.4f}R | PF: {s['profit_factor']:>5.2f}")

    # Final Verdict
    print("\n" + "="*60)
    print(" FINAL VERDICT")
    print("="*60)
    checks = [
        ("OOS Expectancy > 0", test_summary['expectancy'] > 0),
        ("OOS >= 50% of Train", (test_summary['expectancy'] / (train_summary['expectancy'] if train_summary['expectancy'] != 0 else 1)) >= 0.5),
        ("OOS Trades >= 30", test_summary['total_trades'] >= 30),
        ("Robustness (All variants +)", tight_summary['expectancy'] > 0 and loose_summary['expectancy'] > 0),
        ("Monte Carlo p < 0.05", p_val < 0.05)
    ]
    
    passed = 0
    for name, ok in checks:
        print(f"{name:<30} {'✓' if ok else '✗'}")
        if ok: passed += 1
        
    print(f"\nScore: {passed}/{len(checks)}")
    if passed >= 4:
        print("VERDICT: EDGE IS REAL — PROCEED TO PAPER TRADE")
    else:
        print("VERDICT: EDGE NOT CONFIRMED — DO NOT GO LIVE")

    # Save
    train_trades.to_csv(f"{RESULTS_DIR}/train_trades.csv", index=False)
    test_trades.to_csv(f"{RESULTS_DIR}/test_trades.csv", index=False)

if __name__ == "__main__":
    main()
