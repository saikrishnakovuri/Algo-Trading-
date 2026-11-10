import os
import pandas as pd
from backtest_engine import BacktestEngine
import logging
import yaml
from datetime import datetime

# Configuration
DATA_DIR = "data/universe_10d"
INITIAL_CAPITAL = 1000000

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("WeekendBacktest")

def update_strat_config(enabled_strat):
    config_path = "config/strategy_filter.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for strat in config["strategies"]:
        if enabled_strat == "COMBINED":
            config["strategies"][strat]["enabled"] = True
        else:
            config["strategies"][strat]["enabled"] = (strat == enabled_strat)
            
    with open(config_path, "w") as f:
        yaml.dump(config, f)

def run_backtest_for_strategy(strat_name):
    print(f"\n" + "="*60)
    print(f"      BACKTESTING STRATEGY: {strat_name}")
    print("="*60)
    
    update_strat_config(strat_name)
    
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    
    trades = engine.run_massive_backtest_v2(
        files,
        step_size=20 # Balanced for speed and fidelity
    )
    
    if not trades:
        print(f"No trades triggered for {strat_name}")
        return None

    stats = engine.calculate_performance(trades)
    return stats

def main():
    strats = ["MOMENTUM", "MEAN_REVERSION", "SWEEP_RETEST", "COMBINED"]
    results = {}

    for strat in strats:
        stats = run_backtest_for_strategy(strat)
        if stats:
            results[strat] = stats

    print("\n" + "="*80)
    print("      FINAL SUMMARY: STRATEGY COMPARISON (10 SESSIONS)")
    print("="*80)
    print(f"{'STRATEGY':<20} | {'TRADES':<8} | {'WIN %':<8} | {'PNL':<12} | {'RR':<5}")
    print("-" * 60)
    for strat, s in results.items():
        print(f"{strat:<20} | {s['Total Trades']:<8} | {s['Win Rate %']:<8.2f} | {s['Total Profit']:<12.2f} | {s['RR Ratio']:<5.2f}")
    print("="*80)

if __name__ == "__main__":
    main()
