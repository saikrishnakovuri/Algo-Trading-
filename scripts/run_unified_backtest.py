import os
import pandas as pd
import numpy as np
import argparse
import logging
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

# Import engines and adapters
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.strategy_selector import StrategySelector, StrategyResult
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger('unified_backtest')
logger.setLevel(logging.INFO)

# Silence third-party loggers
logging.getLogger("SweepRetest").setLevel(logging.ERROR)
logging.getLogger("StructureStrategy").setLevel(logging.ERROR)
logging.getLogger("live_trader").setLevel(logging.ERROR)

def simulate_trade(df, entry_idx, signal):
    """Simulate a trade outcome based on signal targets/sl using future data."""
    entry = signal.entry
    sl = signal.sl
    target = signal.target1
    direction = signal.direction
    
    risk = abs(entry - sl)
    
    outcome = "PENDING"
    r_multiple = 0.0
    bars_held = 0
    
    # Check next 100 bars for outcome
    for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
        bars_held += 1
        high = df.iloc[j]['High']
        low = df.iloc[j]['Low']
        
        if direction == "CE":
            if low <= sl:
                outcome = "LOSE"
                r_multiple = -1.0
                break
            if high >= target:
                outcome = "WIN"
                r_multiple = (target - entry) / risk if risk > 0 else 0
                break
        else: # PE
            if high >= sl:
                outcome = "LOSE"
                r_multiple = -1.0
                break
            if low <= target:
                outcome = "WIN"
                r_multiple = (entry - target) / risk if risk > 0 else 0
                break
                
    if outcome == "PENDING":
        close_p = df.iloc[min(entry_idx + 100, len(df)-1)]['Close']
        if direction == "CE":
            r_multiple = (close_p - entry) / risk if risk > 0 else 0
        else:
            r_multiple = (entry - close_p) / risk if risk > 0 else 0
        outcome = "WIN" if r_multiple > 0 else "LOSE"
        
    return {
        'outcome': outcome,
        'r_multiple': r_multiple,
        'bars_held': bars_held
    }

def process_single_symbol(args):
    symbol, days, timeframe, idx, total = args
    print(f"Analyzing {symbol} ({idx}/{total})...")
    
    # Re-initialize engines inside worker process
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    sr_engine = SweepRetestEngine(config_path="config/sweep_retest.yaml")
    struct_engine = StructureStrategyEngine(config_path="config/structure_strategy.yaml")
    selector = StrategySelector()
    selector.register("MOMENTUM", mom_engine, momentum_adapter)
    selector.register("MEAN_REVERSION", mr_engine, mean_reversion_adapter)
    selector.register("SWEEP_RETEST", sr_engine, sweep_retest_adapter)
    selector.register("STRUCTURE", struct_engine, structure_strategy_adapter)

    symbol_results = {
        "MOMENTUM": [], "MEAN_REVERSION": [], "SWEEP_RETEST": [], "STRUCTURE": [], "COMBINED": []
    }

    data_path = f"data/universe_10d/{symbol}.csv"
    if not os.path.exists(data_path):
        data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path):
        return symbol_results

    try:
        df_raw = pd.read_csv(data_path)
        if 'Timestamp' in df_raw.columns:
            df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'])
        elif 'date' in df_raw.columns and 'time' in df_raw.columns:
            df_raw['Timestamp'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
        df_raw.set_index('Timestamp', inplace=True)
        df_raw.sort_index(inplace=True)
        
        # Limit to last N days
        cutoff = df_raw.index.max() - timedelta(days=days)
        df_1m = df_raw[df_raw.index >= cutoff]

        if timeframe == '5m':
            df = df_1m.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        else:
            df = df_1m

        if len(df) < 50: return symbol_results

        for i in range(50, len(df)):
            df_slice = df.iloc[:i+1]
            
            # 1. Individual Strategies
            sig_mom = momentum_adapter(mom_engine, df_slice, symbol)
            if sig_mom and sig_mom.confidence_pct >= 65:
                symbol_results["MOMENTUM"].append(simulate_trade(df, i, sig_mom))
                
            sig_mr = mean_reversion_adapter(mr_engine, df_slice, symbol)
            if sig_mr and sig_mr.confidence_pct >= 65:
                symbol_results["MEAN_REVERSION"].append(simulate_trade(df, i, sig_mr))
                
            sig_sr = sweep_retest_adapter(sr_engine, df_slice, symbol, df_1m=df_1m.iloc[:i*5] if timeframe=='5m' else df_slice)
            if sig_sr and sig_sr.confidence_pct >= 65:
                symbol_results["SWEEP_RETEST"].append(simulate_trade(df, i, sig_sr))

            sig_struct = structure_strategy_adapter(struct_engine, df_slice, symbol)
            if sig_struct and sig_struct.confidence_pct >= 75: # Tightened threshold
                symbol_results["STRUCTURE"].append(simulate_trade(df, i, sig_struct))
            
            # 2. Selector
            best_sig = selector.select_best(df_slice, symbol, df_1m=df_1m.iloc[:i*5] if timeframe=='5m' else df_slice)
            if best_sig and best_sig.confidence_pct >= 60:
                symbol_results["COMBINED"].append(simulate_trade(df, i, best_sig))
                
        return symbol_results
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return symbol_results

def run_unified_backtest(symbols, days, timeframe='5m'):
    print("=" * 72)
    print(f"UNIFIED BACKTEST REPORT | {len(symbols)} symbols | {days} days | {timeframe} timeframe")
    print("=" * 72 + "\n")
    
    metrics = {
        "MOMENTUM": {'trades': []}, "MEAN_REVERSION": {'trades': []}, 
        "SWEEP_RETEST": {'trades': []}, "STRUCTURE": {'trades': []}, "COMBINED": {'trades': []}
    }

    args = [(s, days, timeframe, i+1, len(symbols)) for i, s in enumerate(symbols)]
    
    # Use 8 workers for maximum speed
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_single_symbol, args))
        
    for res in results:
        for strat in metrics:
            metrics[strat]['trades'].extend(res[strat])

    print(f"Strategy          | Trades | Win%  | Avg W  | Avg L  | Expect | PF")
    print("-" * 75)
    
    for strat, data in metrics.items():
        trades = data['trades']
        count = len(trades)
        if count == 0:
            print(f"{strat.ljust(17)} |   0    | 0.0%  | +0.0R  | -0.0R  | +0.00R | 0.0")
            continue
            
        wins = [t for t in trades if t['outcome'] == "WIN"]
        losses = [t for t in trades if t['outcome'] == "LOSE"]
        
        win_pct = len(wins) / count * 100
        avg_w = sum([t['r_multiple'] for t in wins]) / len(wins) if wins else 0
        avg_l = sum([t['r_multiple'] for t in losses]) / len(losses) if losses else -1.0
        
        expectancy = (win_pct/100 * avg_w) + ((1 - win_pct/100) * avg_l)
        gross_wins = sum([t['r_multiple'] for t in wins])
        gross_losses = abs(sum([t['r_multiple'] for t in losses]))
        pf = gross_wins / gross_losses if gross_losses > 0 else 99.9
        
        print(f"{strat.ljust(17)} |  {str(count).ljust(5)} | {win_pct:.1f}% | +{avg_w:.1f}R  | {avg_l:.1f}R  | +{expectancy:.2f}R | {pf:.1f}")
        
    print("\n" + "=" * 72)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--symbols", default="")
    args = parser.parse_args()
    
    if args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"]
    
    run_unified_backtest(symbols, args.days)
