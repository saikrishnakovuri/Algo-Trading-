import os
import pandas as pd
import numpy as np
import yaml
import json
import random
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor
from backtest_engine import BacktestEngine
from modules.intermarket.feeds.manager import IntermarketFeedManager
import logging

# Configuration
DATA_DIR = "data/universe_10d"
INITIAL_CAPITAL = 1000000
MAX_WORKERS = 10 

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("TurboBacktest")

STRAT_MAPPING = {
    "MOMENTUM": "BREAKOUT",
    "MEAN_REVERSION": "ZONE_REJECTION",
    "SWEEP_RETEST": "LIQUIDITY_SWEEP",
    "COMBINED": "COMBINED"
}

# Standard Nifty Lists
NIFTY_50_LIST = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"]

NIFTY_100_LIST = NIFTY_50_LIST + ["ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "ATGL", "ABCAPITAL", "AMBUJACEM", "BEL", "BANKBARODA", "BERGEPAINT", "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", "DLF", "DABUR", "GAIL", "GODREJCP", "HAL", "HAVELLS", "ICICIGI", "IDFCFIRSTB", "INDHOTEL", "IOC", "IRCTC", "IRFC", "INDUSTOWER", "INDIGO", "JINDALSTEL", "JIOFIN", "LICHSGFIN", "LICI", "MRF", "MARICO", "MUTHOOTFIN", "NHPC", "NMDC", "NAUKRI", "PAGEIND", "PIDILITIND", "PFC", "PNB", "RECLTD", "SBICARD", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "TATACOMM", "TATAPOWER", "TVSMOTOR", "TORNTPHARM", "TRENT", "UNITDSPR", "VBL", "VEDL", "ZOMATO", "ZYDUSLIFE"]

NIFTY_200_LIST = [
    "360ONE", "ABB", "APLAPOLLO", "AUBANK", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", 
    "ADANIPOWER", "ATGL", "ABCAPITAL", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", 
    "ASTRAL", "AUROPHARMA", "DMART", "AXISBANK", "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", 
    "BAJAJHLDNG", "BANKBARODA", "BANKINDIA", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", 
    "BIOCON", "BLUESTARCO", "BOSCHLTD", "BRITANNIA", "CGPOWER", "CANBK", "CHOLAFIN", "CIPLA", 
    "COALINDIA", "COCHINSHIP", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CUMMINSIND", "DLF", 
    "DABUR", "DIVISLAB", "DIXON", "DRREDDY", "EICHERMOT", "EXIDEIND", "NYKAA", "FEDERALBNK", 
    "FORTIS", "GAIL", "GMRAIRPORT", "GLENMARK", "GODFRYPHLP", "GODREJCP", "GODREJPROP", "GRASIM", 
    "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HAVELLS", "HEROMOTOCO", "HINDALCO", "HAL", 
    "HINDPETRO", "HINDUNILVR", "HINDZINC", "HUDCO", "ICICIBANK", "ICICIGI", "IDFCFIRSTB", "ITC", 
    "INDIANB", "INDHOTEL", "IOC", "IRCTC", "IRFC", "IREDA", "INDUSTOWER", "INDUSINDBK", "NAUKRI", 
    "INFY", "INDIGO", "JSWENERGY", "JSWSTEEL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "KEI", "KPITTECH", 
    "KALYANKJIL", "KOTAKBANK", "LTF", "LICHSGFIN", "LTM", "LT", "LAURUSLABS", "LODHA", "LUPIN", 
    "MRF", "M&MFIN", "M&M", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MOTILALOFS", 
    "MPHASIS", "MCX", "MUTHOOTFIN", "NHPC", "NMDC", "NTPC", "NATIONALUM", "NESTLEIND", "OBEROIRLTY", 
    "ONGC", "OIL", "PAYTM", "OFSS", "POLICYBZR", "PIIND", "PAGEIND", "PATANJALI", "PERSISTENT", 
    "PHOENIXLTD", "PIDILITIND", "POLYCAB", "PFC", "POWERGRID", "PRESTIGE", "PNB", "RECLTD", "RADICO", 
    "RVNL", "RELIANCE", "SBICARD", "SBILIFE", "SRF", "MOTHERSON", "SHREECEM", "SHRIRAMFIN", "SIEMENS", 
    "SOLARINDS", "SBIN", "SAIL", "SUNPHARMA", "SUPREMEIND", "SUZLON", "TVSMOTOR", "TATACOMM", "TCS", 
    "TATACONSUM", "TATAELXSI", "TATAINVEST", "TATAPOWER", "TATASTEEL", "TECHM", "TITAN", "TORNTPHARM", 
    "TRENT", "TIINDIA", "UPL", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "VBL", "VEDL", "IDEA", "VOLTAS", 
    "WIPRO", "YESBANK", "ZYDUSLIFE"
]

def get_universe_selection():
    all_local_files = [f.replace(".csv", "") for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    
    # 1. Nifty 100 present locally
    group_a = [s for s in NIFTY_100_LIST if s in all_local_files]
    
    # 2. 50 Random from Next 100 (Nifty 200 - Nifty 100)
    n200_pool = [s for s in NIFTY_200_LIST if s in all_local_files and s not in NIFTY_100_LIST]
    group_b = random.sample(n200_pool, min(50, len(n200_pool)))
    
    # 3. Fill the rest from the 987 symbols to hit exactly 200
    current_selection = list(set(group_a + group_b))
    target_total = 200
    needed = target_total - len(current_selection)
    
    rest_pool = [s for s in all_local_files if s not in current_selection]
    group_c = random.sample(rest_pool, min(needed, len(rest_pool)))
    
    final_list = current_selection + group_c
    nifty50_present = set([s for s in NIFTY_50_LIST if s in all_local_files])
    
    return [os.path.join(DATA_DIR, s + ".csv") for s in final_list], nifty50_present

def update_strat_config(enabled_strat):
    config_path = "config/strategy_filter.yaml"
    with open(config_path, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    actual_strat = STRAT_MAPPING.get(enabled_strat, enabled_strat)
    
    for strat in config["strategies"]:
        if actual_strat == "COMBINED":
            config["strategies"][strat]["enabled"] = True
        else:
            config["strategies"][strat]["enabled"] = (strat == actual_strat)
    with open(config_path, "w", encoding='utf-8') as f:
        yaml.dump(config, f)

def run_single_symbol(args):
    file_path, strat_name, initial_capital = args
    actual_strat = STRAT_MAPPING.get(strat_name, strat_name)
    try:
        engine = BacktestEngine(initial_capital=initial_capital)
        trades = engine.run_massive_backtest_v2(
            [file_path], 
            strategy_isolation_filter=actual_strat,
            step_size=20 
        )
        return trades
    except Exception as e:
        return []

def run_turbo_backtest(strat_name, selected_files, nifty50_set):
    print(f"\n>>> STARTING TURBO BACKTEST: {strat_name} (Parallel Mode on {len(selected_files)} Stocks)")
    update_strat_config(strat_name)
    
    args = [(f, strat_name, INITIAL_CAPITAL) for f in selected_files]
    
    all_trades = []
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(run_single_symbol, args))
        for res in results:
            all_trades.extend(res)
            
    if not all_trades:
        print(f"No trades triggered for {strat_name}")
        return None, None

    # Group results
    nifty50_trades = [t for t in all_trades if t.get('symbol', '') in nifty50_set]
    other_trades = [t for t in all_trades if t.get('symbol', '') not in nifty50_set]

    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    n_stats = engine.calculate_performance(nifty50_trades)
    o_stats = engine.calculate_performance(other_trades)
    
    return n_stats, o_stats

def main():
    strats = ["MOMENTUM", "MEAN_REVERSION", "SWEEP_RETEST"]
    final_results = {}

    start_time = datetime.now()
    
    selected_files, nifty50_set = get_universe_selection()
    print(f"Total Selected: {len(selected_files)} symbols")
    print(f"Nifty 50 Group: {len(nifty50_set)} symbols")
    print(f"Other 150 Group: {len(selected_files) - len(nifty50_set)} symbols")

    for strat in strats:
        n_stats, o_stats = run_turbo_backtest(strat, selected_files, nifty50_set)
        if n_stats or o_stats:
            final_results[strat] = {"nifty": n_stats, "other": o_stats}
            print(f"DONE: {strat} | Nifty50 PnL: {n_stats['Total Profit'] if n_stats else 0} | Other PnL: {o_stats['Total Profit'] if o_stats else 0}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60

    print("\n" + "="*95)
    print(f"      TURBO SUMMARY (200 SYMBOLS): Completed in {duration:.1f} mins")
    print("="*95)
    print(f"{'STRATEGY':<20} | {'GROUP':<12} | {'TRADES':<8} | {'WIN %':<8} | {'PNL':<12} | {'RR':<5}")
    print("-" * 90)
    
    for strat, res in final_results.items():
        n = res["nifty"]
        o = res["other"]
        if n:
            print(f"{strat:<20} | {'NIFTY 50':<12} | {n['Total Trades']:<8} | {n['Win Rate %']:<8.2f} | {n['Total Profit']:<12.2f} | {n['RR Ratio']:<5.2f}")
        if o:
            print(f"{'':<20} | {'OTHER 150':<12} | {o['Total Trades']:<8} | {o['Win Rate %']:<8.2f} | {o['Total Profit']:<12.2f} | {o['RR Ratio']:<5.2f}")
        print("-" * 90)
    print("="*95)

if __name__ == "__main__":
    main()
