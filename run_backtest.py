#!/usr/bin/env python3
"""
AUTHORITATIVE BACKTEST RUNNER
All backtests must go through this script to ensure consistent 
configuration. Do not bypass this with custom scripts.
"""
import argparse
import yaml
import sys
import os
from datetime import datetime

def load_master_config():
    """Load ALL configs that affect trading decisions."""
    configs = {}
    config_files = [
        "config/regime.yaml",
        "config/vp_avwap.yaml",
        "config/smc.yaml",
        "config/context_filters.yaml",
        "config/risk_execution.yaml",
        "config/intermarket.yaml",
        "config/universe.yaml",
        "config/strategy_filter.yaml",
        "config/paper_mode.yaml",
    ]
    for f in config_files:
        try:
            with open(f, encoding="utf-8") as fh:
                key = f.split("/")[-1].replace(".yaml", "")
                configs[key] = yaml.safe_load(fh)
        except FileNotFoundError:
            print(f"WARNING: {f} not found!")
    return configs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", 
                        default=None,
                        help="Stock symbols to test")
    parser.add_argument("--days", type=int, default=30,
                        help="Number of days to backtest")
    parser.add_argument("--capital", type=float, 
                        default=1000000,
                        help="Starting capital in INR")
    parser.add_argument("--data-source", 
                        choices=["angel_historical", "csv"],
                        default="angel_historical")
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    args = parser.parse_args()
    
    # Load master config
    config = load_master_config()
    
    # Verify critical configs are present
    if "strategy_filter" not in config:
        print("FATAL: config/strategy_filter.yaml missing!")
        print("Cannot run without strategy filter. Aborting.")
        sys.exit(1)
    
    # Print active configuration summary
    sf = config["strategy_filter"]["strategies"]
    print("=" * 60)
    print("BACKTEST CONFIGURATION SUMMARY")
    print("=" * 60)
    for strat, cfg in sf.items():
        status = "ENABLED" if cfg.get("enabled") else "DISABLED"
        scope = cfg.get("allowed_symbols", "ALL")
        override = cfg.get("min_score_override", "default")
        print(f"  {strat:<22} {status:<10} Scope: {scope}  MinScore: {override}")
    print("=" * 60)
    
    # Import and run the calibrated BacktestEngine
    from backtest_engine import BacktestEngine
    
    # Ensure BacktestEngine uses the session IDs for consistency
    session_id = f"unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    engine = BacktestEngine(initial_capital=args.capital)
    engine.journal_file = f"trade_journal_{session_id}.csv"
    
    # Patch the meta-tracker to use a specific DB for this run
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = f"meta_db_{session_id}.json"
    
    # Determine files to process
    if args.data_source == "angel_historical":
        data_dir = "data/angel_historical"
    else:
        data_dir = "data/nifty200"
        
    if args.symbols:
        symbols = args.symbols
    else:
        # Default symbols as per calibrated universe
        symbols = [
            "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
            "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"
        ]
        
    all_files = []
    for s in symbols:
        file_path = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(file_path):
            all_files.append(file_path)
        else:
            print(f"WARNING: Data file for {s} not found at {file_path}")

    if not all_files:
        print("ERROR: No data files found for backtest. Aborting.")
        sys.exit(1)

    print(f"Starting Unified Backtest on {len(all_files)} symbols...")
    
    # Run Backtest
    trades = engine.run_massive_backtest_v2(all_files, start_date=args.start_date, end_date=args.end_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*50)
        print("UNIFIED BACKTEST RESULTS")
        print("="*50)
        for k, v in stats.items():
            print(f"{k:20}: {v}")
        print("="*50)
        print(f" Journal: {engine.journal_file}")
        print(f" Meta DB: {meta_learning.tracker.DB_FILE}")
    else:
        print("No trades triggered with current strict filters.")

if __name__ == "__main__":
    main()
