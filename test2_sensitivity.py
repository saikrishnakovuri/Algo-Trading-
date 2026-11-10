"""
OOS Validation - Test 2: Parameter Sensitivity
"""
import os
import json
import pandas as pd
from modules.cached_data_loader import CachedDataLoader
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine

# CONFIG
RESULTS_DIR = "data/backtest_results/oos_validation"
CAPITAL = 1000000
RISK_PER_TRADE_PCT = 0.01
TIME_STOP_SLIPPAGE = 0.5
STEP_SIZE = 10
TRADE_START = "09:20"
TRADE_END = "14:30"

def execute_trade_sim(df, entry_idx, signal, capital):
    entry, sl, target, direction = signal.entry, signal.sl, signal.target1, signal.direction
    if not all([entry, sl, target]): return None
    dist = abs(entry - sl); qty = int((capital * RISK_PER_TRADE_PCT) / dist) if dist > 0 else 1
    max_hold = 6 if signal.strategy_name == "MEAN_REVERSION" else 10
    trade_future = df.iloc[entry_idx + 1 : entry_idx + 1 + max_hold]
    if trade_future.empty: return None
    exit_p, exit_t, bars = None, None, 0
    for i, (_, row) in enumerate(trade_future.iterrows()):
        bars = i + 1; low, high = row['Low'], row['High']
        if direction in ['CE', 'LONG']:
            if low <= sl: exit_p = sl; exit_t = "SL_HIT"; break
            if high >= target: exit_p = target; exit_t = "TARGET_HIT"; break
        else:
            if high >= sl: exit_p = sl; exit_t = "SL_HIT"; break
            if low <= target: exit_p = target; exit_t = "TARGET_HIT"; break
    if exit_p is None:
        exit_p = float(trade_future.iloc[-1]['Close'])
        exit_p = exit_p - TIME_STOP_SLIPPAGE if direction in ['CE', 'LONG'] else exit_p + TIME_STOP_SLIPPAGE
        exit_t, bars = "TIME_STOP", len(trade_future)
    return round((exit_p - entry if direction in ['CE', 'LONG'] else entry - exit_p) / dist, 3)

def run_sim(data_dict, sel):
    results = []
    for sym, df in data_dict.items():
        days = df.groupby(df.index.date)
        for date, day_df in days:
            day_data = day_df.between_time(TRADE_START, TRADE_END)
            for i in range(0, len(day_data), STEP_SIZE):
                global_idx = df.index.get_loc(day_data.index[i])
                best_sig = sel.select_best(df.iloc[max(0, global_idx-100):global_idx+1], sym)
                if best_sig:
                    r = execute_trade_sim(df, global_idx, best_sig, CAPITAL)
                    if r is not None: results.append(r); break
    return pd.Series(results).mean() if results else 0

def main():
    loader = CachedDataLoader()
    symbols = loader.get_available_symbols(interval="5m")[:10]
    data = {s: loader.load(s, "5m") for s in symbols}
    mom = MomentumBreakoutEngine()
    
    variants = [
        ("BASELINE", 6),
        ("TIGHTER (min=7)", 7),
        ("LOOSER (min=5)", 5)
    ]
    
    final_results = {}
    print("PARAMETER SENSITIVITY (MR min_score)")
    print(f"{'Variant':<20} {'Expectancy':>10}")
    for label, score in variants:
        mr = MeanReversionEngine(config_path="config/mean_reversion.yaml")
        mr.min_score = score
        sel = StrategySelector(); sel.register("MOM", mom, momentum_adapter); sel.register("MR", mr, mean_reversion_adapter)
        exp = run_sim(data, sel)
        final_results[label] = exp
        print(f"{label:<20} {exp:>+10.4f}R")
        
    with open(f"{RESULTS_DIR}/sensitivity.json", "w") as f: json.dump(final_results, f)

if __name__ == "__main__":
    main()
