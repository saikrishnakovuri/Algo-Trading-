#!/usr/bin/env python3
"""
Authoritative Combined Multi-Strategy Backtest
══════════════════════════════════════════════
Runs Momentum, Candlestick, and Mean Reversion engines across all cached symbols.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime
from modules.cached_data_loader import CachedDataLoader
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, candlestick_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.candlestick_engine import CandlestickEngine
from modules.mean_reversion_engine import MeanReversionEngine

# ── CONFIGURATION ───────────────────────────────────────────────────────────
CAPITAL = 1000000.0  # 10 Lakhs
RISK_PER_TRADE = 0.01  # 1%
MAX_CONCURRENT_TRADES = 3
SLIPPAGE_POINTS = 0.5  # for time-stop market exits
# ─────────────────────────────────────────────────────────────────────────────

def get_lot_size(entry_price):
    """Simple lot size logic - 1 share for stocks."""
    return 1

def execute_trade(df, entry_idx, signal, capital):
    """
    Simulates trade outcome from entry_idx forward.
    """
    entry = signal.entry
    sl = signal.sl
    target = signal.target1
    direction = signal.direction # 'CE' (Long) or 'PE' (Short)
    
    if not all([entry, sl, target]): return None
    
    dist_to_sl = abs(entry - sl)
    if dist_to_sl == 0: return None
    
    # Position Sizing
    risk_amount = capital * RISK_PER_TRADE
    qty = int(risk_amount / dist_to_sl)
    if qty <= 0: qty = 1
    
    # Max hold bars based on strategy
    if signal.strategy_name == "MEAN_REVERSION":
        max_hold = 6
    else:
        max_hold = 10
        
    # Walk forward
    bars_held = 0
    exit_price = None
    exit_type = None
    
    trade_future = df.iloc[entry_idx + 1 : entry_idx + 1 + max_hold]
    if trade_future.empty:
        return None
        
    for i, (_, row) in enumerate(trade_future.iterrows()):
        bars_held = i + 1
        low, high, close = row['Low'], row['High'], row['Close']
        
        if direction == 'CE':
            # LONG
            if low <= sl and high >= target:
                # Both hit - conservative: SL hit first
                exit_price = sl
                exit_type = "SL_HIT"
                break
            elif low <= sl:
                exit_price = sl
                exit_type = "SL_HIT"
                break
            elif high >= target:
                exit_price = target
                exit_type = "TARGET_HIT"
                break
        else:
            # SHORT
            if high >= sl and low <= target:
                exit_price = sl
                exit_type = "SL_HIT"
                break
            elif high >= sl:
                exit_price = sl
                exit_type = "SL_HIT"
                break
            elif low <= target:
                exit_price = target
                exit_type = "TARGET_HIT"
                break
                
    if exit_price is None:
        # Time stop
        exit_price = float(trade_future.iloc[-1]['Close'])
        # Apply slippage for market exit
        if direction == 'CE':
            exit_price -= SLIPPAGE_POINTS
        else:
            exit_price += SLIPPAGE_POINTS
        exit_type = "TIME_STOP"
        bars_held = len(trade_future)

    pnl_points = (exit_price - entry) if direction == 'CE' else (entry - exit_price)
    pnl_inr = pnl_points * qty
    r_multiple = pnl_points / dist_to_sl
    
    return {
        'Symbol': '', # to be filled by caller
        'Date': str(df.index[entry_idx].date()),
        'Timestamp': str(df.index[entry_idx]),
        'Strategy': signal.strategy_name,
        'Pattern': signal.setup_type,
        'Direction': direction,
        'Entry': round(entry, 2),
        'SL': round(sl, 2),
        'Target': round(target, 2),
        'Exit': round(exit_price, 2),
        'Exit_Type': exit_type,
        'Bars_Held': bars_held,
        'P&L_Points': round(pnl_points, 2),
        'P&L_INR': round(pnl_inr, 2),
        'R_Multiple': round(r_multiple, 3)
    }

def main():
    import argparse
    import yaml
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-symbols", type=int, default=60)
    parser.add_argument("--step-size", type=int, default=5)
    args = parser.parse_args()

    # Load Multi-Strategy Config
    with open("config/multi_strategy.yaml", "r") as f:
        ms_config = yaml.safe_load(f)

    print("=== STARTING COMBINED MULTI-STRATEGY BACKTEST ===")
    
    loader = CachedDataLoader()
    sel = StrategySelector()
    
    # Register Engines based on config
    if ms_config['strategies'].get('momentum_breakout', {}).get('enabled', True):
        momentum_engine = MomentumBreakoutEngine()
        sel.register("MOMENTUM", momentum_engine, momentum_adapter)
        print("Registered MOMENTUM engine")
        
    if ms_config['strategies'].get('candlestick_patterns', {}).get('enabled', False):
        candlestick_engine = CandlestickEngine(config_path="config/candlestick.yaml")
        sel.register("CANDLESTICK", candlestick_engine, candlestick_adapter)
        print("Registered CANDLESTICK engine")
        
    if ms_config['strategies'].get('mean_reversion', {}).get('enabled', True):
        mean_reversion_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
        sel.register("MEAN_REVERSION", mean_reversion_engine, mean_reversion_adapter)
        print("Registered MEAN_REVERSION engine")
    
    symbols = loader.get_available_symbols(interval="5m")[:args.max_symbols]
    print(f"Total symbols to process: {len(symbols)}")
    
    all_trades = []
    symbol_last_trade_date = {}
    
    for idx, sym in enumerate(symbols):
        print(f"[{idx+1}/{len(symbols)}] Processing {sym}...")
            
        df = loader.load(sym, interval="5m")
        if df is None or len(df) < 50:
            continue
            
        # Group by day
        days = df.groupby(df.index.date)
        
        for date, day_df in days:
            # Skip first bar (opening noise)
            day_data = day_df.between_time('09:20', '14:30')
            if day_data.empty: continue
            
            # Bar-by-bar simulation
            for i in range(0, len(day_data), args.step_size):
                current_timestamp = day_data.index[i]
                
                # Risk check: Max 1 trade per symbol per day
                if symbol_last_trade_date.get(sym) == date:
                    continue
                    
                # Get slice of data for indicators (limit to last 100 bars for speed)
                global_idx = df.index.get_loc(current_timestamp)
                df_slice = df.iloc[max(0, global_idx-100):global_idx+1]
                
                best_sig = sel.select_best(df_slice, sym)
                
                if best_sig:
                    # Execute trade
                    trade = execute_trade(df, global_idx, best_sig, CAPITAL)
                    if trade:
                        trade['Symbol'] = sym
                        all_trades.append(trade)
                        symbol_last_trade_date[sym] = date
                        break # Only 1 trade per day per symbol
    
    print(f"\nBacktest complete. Total trades triggered: {len(all_trades)}")
    
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        os.makedirs("data/backtest_results", exist_ok=True)
        trades_df.to_csv("data/backtest_results/combined_backtest_results.csv", index=False)
        print("Results saved to data/backtest_results/combined_backtest_results.csv")
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    main()
