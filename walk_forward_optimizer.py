import os
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_engine import BacktestEngine
import logging
import sys
import shutil

# ── CONFIGURATION ───────────────────────────────────────────────────────────
DATA_DIR = "data/angel_historical"
OPTIMIZATION_DIR = "data/optimization"
HISTORY_FILE = os.path.join(OPTIMIZATION_DIR, "param_history.json")
SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]

WINDOWS = [
    {"train": ("2026-01-01", "2026-03-31"), "test": ("2026-04-01", "2026-04-24")},
]

# ── EXTENDED PARAMETER GRID ────────────────────────────────────────────────
GRID = {
    "GENERAL": {
        "target_r_multiple": [1.2, 1.5, 2.0],
        "min_score": [5.5, 6.5]
    },
    "MOMENTUM": {
        "range_atr_threshold": [4.0, 5.0, 6.0],
        "consolidation_bars": [5, 10],
        "volume_breakout_ratio": [1.2, 1.5]
    },
    "MEAN_REVERSION": {
        "rsi_oversold": [25, 30, 35],
        "rsi_overbought": [65, 70, 75],
        "atr_sl_multiplier": [0.4, 0.6, 0.8]
    },
    "SWEEP_RETEST": {
        "min_wick_body_ratio": [1.5, 2.0, 2.5],
        "max_bars_sweep_to_retest": [15, 25, 35]
    }
}

os.makedirs(OPTIMIZATION_DIR, exist_ok=True)
os.makedirs("config/backups", exist_ok=True)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler("logs/wfo_enhanced.log"), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("WFO")

def backup_config():
    date_str = datetime.now().strftime("%Y%m%d")
    for cfg in ["strategy_filter.yaml", "momentum.yaml", "mean_reversion.yaml", "sweep_retest.yaml"]:
        src = f"config/{cfg}"
        if os.path.exists(src):
            shutil.copy(src, f"config/backups/{cfg.split('.')[0]}_{date_str}.yaml")

def load_current_params():
    params = {}
    try:
        with open("config/strategy_filter.yaml", "r", encoding='utf-8') as f:
            sf = yaml.safe_load(f)
            params['min_score'] = sf['strategies']['MOMENTUM']['min_score_override']
    except: params['min_score'] = 5.5
    return params

def update_configs(params):
    # 1. Strategy Filter (Min Score)
    sf_path = "config/strategy_filter.yaml"
    if os.path.exists(sf_path):
        with open(sf_path, "r", encoding='utf-8') as f: sf = yaml.safe_load(f)
        for s in sf['strategies']:
            sf['strategies'][s]['min_score_override'] = float(params.get('min_score', 5.5))
        with open(sf_path, "w", encoding='utf-8') as f: yaml.dump(sf, f)

    # 2. Momentum
    mom_path = "config/momentum.yaml"
    mom_cfg = {
        "range_atr_threshold": params.get('range_atr_threshold', 5.0),
        "consolidation_bars": params.get('consolidation_bars', 5),
        "volume_breakout_ratio": params.get('volume_breakout_ratio', 1.3)
    }
    with open(mom_path, "w", encoding='utf-8') as f: yaml.dump(mom_cfg, f)

    # 3. Mean Reversion
    mr_path = "config/mean_reversion.yaml"
    if os.path.exists(mr_path):
        with open(mr_path, "r", encoding='utf-8') as f: mr = yaml.safe_load(f)
        mr['indicators']['rsi_oversold'] = params.get('rsi_oversold', 30)
        mr['indicators']['rsi_overbought'] = params.get('rsi_overbought', 70)
        mr['risk']['sl_atr_multiplier'] = params.get('atr_sl_multiplier', 0.5)
        with open(mr_path, "w", encoding='utf-8') as f: yaml.dump(mr, f)

    # 4. Sweep Retest
    sr_path = "config/sweep_retest.yaml"
    if os.path.exists(sr_path):
        with open(sr_path, "r", encoding='utf-8') as f: sr = yaml.safe_load(f)
        sr['confirmation']['rejection_candle']['min_wick_to_body'] = params.get('min_wick_body_ratio', 2.0)
        sr['state_machine']['max_bars_sweep_to_retest'] = params.get('max_bars_sweep_to_retest', 20)
        with open(sr_path, "w", encoding='utf-8') as f: yaml.dump(sr, f)

def record_history(run_data):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding='utf-8') as f: history = json.load(f)
    history.append(run_data)
    with open(HISTORY_FILE, "w", encoding='utf-8') as f: json.dump(history, f, indent=2)

def detect_drift():
    if not os.path.exists(HISTORY_FILE): return
    with open(HISTORY_FILE, "r", encoding='utf-8') as f: history = json.load(f)
    if len(history) < 5: return
    accepted = [h for h in history if h.get('accepted', False)][-5:]
    if len(accepted) < 5: return
    params = accepted[0]['params'].keys()
    for p in params:
        values = [h['params'][p] for h in accepted]
        if all(x < y for x, y in zip(values, values[1:])):
            logger.warning(f"[DRIFT] Parameter {p} is consistently INCREASING: {values}")
        elif all(x > y for x, y in zip(values, values[1:])):
            logger.warning(f"[DRIFT] Parameter {p} is consistently DECREASING: {values}")

def run_enhanced_wfo():
    backup_config()
    current_params = load_current_params()
    files = [os.path.join(DATA_DIR, f"{s}_1m.csv") for s in SYMBOLS if os.path.exists(os.path.join(DATA_DIR, f"{s}_1m.csv"))]
    best_expectancy = -999
    best_params = None
    
    # 1. OPTIMIZATION
    for r in [1.5, 2.0]:
        for score in [5.5, 6.5]:
            test_params = {"target_r_multiple": r, "min_score": score}
            update_configs(test_params)
            engine = BacktestEngine(initial_capital=1000000)
            trades = engine.run_massive_backtest_v2(files, start_date=WINDOWS[0]['train'][0], end_date=WINDOWS[0]['train'][1], target_r_multiple=r, step_size=30)
            stats = engine.calculate_performance(trades)
            wr = stats["Win Rate %"] / 100; rr = stats["RR Ratio"]
            exp = (wr * rr) - (1 - wr) if stats["Total Trades"] >= 2 else -999
            if exp > best_expectancy:
                best_expectancy = exp
                best_params = test_params.copy()

    if best_params:
        logger.info(f"IS Optimal Params: {best_params} (Exp: {best_expectancy:.3f})")
        # 2. VALIDATION
        update_configs(current_params)
        engine = BacktestEngine(initial_capital=1000000)
        c_trades = engine.run_massive_backtest_v2(files, start_date=WINDOWS[0]['test'][0], end_date=WINDOWS[0]['test'][1], target_r_multiple=1.5, step_size=20)
        c_stats = engine.calculate_performance(c_trades)
        c_exp = (c_stats["Win Rate %"]/100 * c_stats["RR Ratio"]) - (1 - c_stats["Win Rate %"]/100)
        
        update_configs(best_params)
        engine = BacktestEngine(initial_capital=1000000)
        n_trades = engine.run_massive_backtest_v2(files, start_date=WINDOWS[0]['test'][0], end_date=WINDOWS[0]['test'][1], target_r_multiple=best_params['target_r_multiple'], step_size=20)
        n_stats = engine.calculate_performance(n_trades)
        n_exp = (n_stats["Win Rate %"]/100 * n_stats["RR Ratio"]) - (1 - n_stats["Win Rate %"]/100)
        
        # 3. SAFETY RAILS
        accepted = True
        improvement = (n_exp - c_exp) / abs(c_exp) if c_exp != 0 else 1.0
        if improvement < 0.05 and n_exp <= c_exp: accepted = False
        
        if accepted:
            update_configs(best_params)
            logger.info("New params accepted.")
        else:
            update_configs(current_params)
            logger.info("New params rejected.")
            
        record_history({"date": datetime.now().strftime("%Y-%m-%d"), "params": best_params, "accepted": accepted, "improvement": improvement})
        detect_drift()

if __name__ == "__main__":
    run_enhanced_wfo()
