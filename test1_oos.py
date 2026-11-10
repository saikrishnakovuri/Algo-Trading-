"""
OOS Validation - Test 1: Train/Test Split
"""
import os
import pandas as pd
import numpy as np
from modules.cached_data_loader import CachedDataLoader
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine

# CONFIG
CACHE_DIR = "data/cache"
RESULTS_DIR = "data/backtest_results/oos_validation"
TRAIN_RATIO = 0.70
CAPITAL = 1000000
RISK_PER_TRADE_PCT = 0.01
TIME_STOP_SLIPPAGE = 0.5
STEP_SIZE = 10
TRADE_START = "09:20"
TRADE_END = "14:30"

os.makedirs(RESULTS_DIR, exist_ok=True)

def execute_trade_sim(df, entry_idx, signal, capital):
    entry, sl, target, direction = signal.entry, signal.sl, signal.target1, signal.direction
    if not all([entry, sl, target]): return None
    dist_to_sl = abs(entry - sl)
    if dist_to_sl == 0: return None
    qty = int((capital * RISK_PER_TRADE_PCT) / dist_to_sl)
    if qty <= 0: qty = 1
    max_hold = 6 if signal.strategy_name == "MEAN_REVERSION" else 10
    trade_future = df.iloc[entry_idx + 1 : entry_idx + 1 + max_hold]
    if trade_future.empty: return None
    exit_price, exit_type, bars_held = None, None, 0
    for i, (_, row) in enumerate(trade_future.iterrows()):
        bars_held = i + 1
        low, high = row['Low'], row['High']
        if direction in ['CE', 'LONG']:
            if low <= sl: exit_price = sl; exit_type = "SL_HIT"; break
            if high >= target: exit_price = target; exit_type = "TARGET_HIT"; break
        else:
            if high >= sl: exit_price = sl; exit_type = "SL_HIT"; break
            if low <= target: exit_price = target; exit_type = "TARGET_HIT"; break
    if exit_price is None:
        exit_price = float(trade_future.iloc[-1]['Close'])
        exit_price = exit_price - TIME_STOP_SLIPPAGE if direction in ['CE', 'LONG'] else exit_price + TIME_STOP_SLIPPAGE
        exit_type, bars_held = "TIME_STOP", len(trade_future)
    pnl_points = (exit_price - entry) if direction in ['CE', 'LONG'] else (entry - exit_price)
    return {'Symbol': '', 'Date': str(df.index[entry_idx].date()), 'Strategy': signal.strategy_name, 'Direction': direction, 'Entry': round(entry, 2), 'SL': round(sl, 2), 'Target': round(target, 2), 'Exit': round(exit_price, 2), 'Exit_Type': exit_type, 'Bars_Held': bars_held, 'P&L_INR': round(pnl_points * qty, 2), 'R_Multiple': round(pnl_points / dist_to_sl, 3)}

def run_backtest(data_dict, sel):
    all_trades = []
    symbol_last_trade_date = {}
    for sym in sorted(data_dict.keys()):
        df = data_dict[sym]
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
                    if trade: trade['Symbol'] = sym; all_trades.append(trade); symbol_last_trade_date[sym] = date; break
    return pd.DataFrame(all_trades)

def compute_summary(trades_df, label):
    if trades_df.empty: return {'label': label, 'total_trades': 0, 'win_rate': 0, 'expectancy': 0, 'profit_factor': 0}
    wins, losses = trades_df[trades_df['R_Multiple'] > 0], trades_df[trades_df['R_Multiple'] <= 0]
    avg_r = trades_df['R_Multiple'].mean()
    gp, gl = wins['R_Multiple'].sum(), abs(losses['R_Multiple'].sum())
    return {'label': label, 'total_trades': len(trades_df), 'win_rate': round(len(wins)/len(trades_df)*100, 1), 'expectancy': round(avg_r, 4), 'profit_factor': round(gp / (gl if gl > 0 else 0.001), 2)}

def main():
    loader = CachedDataLoader()
    all_symbols = loader.get_available_symbols(interval="5m")[:20]
    all_data, all_dates = {}, set()
    for sym in all_symbols:
        df = loader.load(sym, interval="5m")
        if df is not None and len(df) > 50: all_data[sym] = df; all_dates.update(df.index.date)
    sorted_dates = sorted(list(all_dates))
    cutoff = sorted_dates[int(len(sorted_dates) * TRAIN_RATIO)]
    train_data = {s: df[df.index.date < cutoff] for s, df in all_data.items()}
    test_data = {s: df[df.index.date >= cutoff] for s, df in all_data.items()}
    sel = StrategySelector()
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
    print(f"Running TRAIN (cutoff {cutoff})...")
    train_trades = run_backtest(train_data, sel)
    print(f"Running TEST (OOS)...")
    test_trades = run_backtest(test_data, sel)
    train_summary = compute_summary(train_trades, "TRAIN")
    test_summary = compute_summary(test_trades, "TEST (OOS)")
    print("\nTRAIN vs TEST COMPARISON")
    print(f"{'Metric':<15} {'TRAIN':>10} {'TEST':>10} {'Delta':>10}")
    for m in ['total_trades', 'win_rate', 'expectancy', 'profit_factor']:
        tr, ts = train_summary[m], test_summary[m]
        print(f"{m:<15} {tr:>10} {ts:>10} {ts-tr:>+10.4f}")
    train_trades.to_csv(f"{RESULTS_DIR}/train_trades.csv", index=False)
    test_trades.to_csv(f"{RESULTS_DIR}/test_trades.csv", index=False)
    with open(f"{RESULTS_DIR}/summary_oos.json", "w") as f: json.dump({'train': train_summary, 'test': test_summary}, f)

if __name__ == "__main__":
    import json
    main()
