import os
import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime, time
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.price_action_engine import PriceActionEngine
from modules.trailing_sl_manager import TrailingSLManager, ManagedTrade

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('backtest')

# 1. SECTOR RISK CHEAT SHEET
SECTOR_MAP = {
    "NIFTY_BANK": {"target_pct": 0.012, "sl_pct": 0.006, "label": "BANKING"},
    "NIFTY_IT": {"target_pct": 0.010, "sl_pct": 0.005, "label": "IT"},
    "NIFTY_FMCG": {"target_pct": 0.007, "sl_pct": 0.004, "label": "FMCG"},
    "NIFTY_AUTO": {"target_pct": 0.015, "sl_pct": 0.008, "label": "AUTO"},
    "NIFTY_ENERGY": {"target_pct": 0.014, "sl_pct": 0.0065, "label": "ENERGY"},
    "NIFTY_METAL": {"target_pct": 0.020, "sl_pct": 0.010, "label": "METAL"},
    "NIFTY_FINSERV": {"target_pct": 0.025, "sl_pct": 0.012, "label": "HIGH_VOL"},
    "HIGH_VOL": {"target_pct": 0.025, "sl_pct": 0.012, "label": "HIGH_VOL"},
}

DEFAULT_RISK = {"target_pct": 0.010, "sl_pct": 0.005, "label": "STANDARD"}

def get_sector_params(symbol, sector_name):
    if symbol in ["ADANIENT", "ADANIPORTS", "BAJFINANCE"]:
        return SECTOR_MAP["HIGH_VOL"]
    return SECTOR_MAP.get(sector_name, DEFAULT_RISK)

def run_backtest(symbol, file_path, universe_map, sl_mode="RR_2_1"):
    df_raw = pd.read_csv(file_path, index_col=0, parse_dates=True)
    if df_raw.empty: return None
    
    # Last 60 days
    df = df_raw.last('60D')
    df_5m = PriceActionEngine.resample_data(df, '5min')
    
    # Setup Engines
    sel = StrategySelector()
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
    
    # Programmatic TSL Config
    tsl_config = {
        'enabled': True,
        'partial_exits': [
            {'r_multiple': 2.0, 'exit_pct': 20}, 
            {'r_multiple': 3.0, 'exit_pct': 20}, 
            {'r_multiple': 4.0, 'exit_pct': 20}, 
            {'r_multiple': 5.0, 'exit_pct': 20}, 
            {'r_multiple': 6.0, 'exit_pct': 20}, 
        ],
        'min_remaining_qty': 1,
        'round_qty_to': 1,
        'paper_mode': {'use_high_low_for_exits': True, 'same_bar_conflict': 'conservative'}
    }
    
    tsl_manager = TrailingSLManager()
    tsl_manager.config = tsl_config
    
    sector = universe_map.get(symbol, {}).get('sector', 'UNKNOWN')
    risk_params = get_sector_params(symbol, sector)
    
    trades_log = []
    active_trade = None
    fixed_capital = 100000.0
    
    for i in range(100, len(df_5m)):
        current_time = df_5m.index[i].time()
        if current_time < time(9, 20) or current_time > time(15, 20): continue
        
        # 1. Check Exit
        if active_trade:
            row_1m = df.loc[df_5m.index[i-1] : df_5m.index[i]]
            for _, tick in row_1m.iterrows():
                events = tsl_manager.check_exits(active_trade, tick['High'], tick['Low'], tick['Close'])
                for ev in events:
                    trades_log.append({'pnl': ev['pnl']})
                if active_trade.is_closed:
                    active_trade = None
                    break
        
        # 2. Check Entry
        if not active_trade and current_time < time(14, 30):
            window = df_5m.iloc[i-100:i+1]
            sig = sel.select_best(window, symbol)
            
            if sig and sig.confidence_pct >= 60:
                entry_price = sig.entry
                qty = int(fixed_capital / entry_price)
                
                # SL Logic Comparison
                target_dist = entry_price * risk_params['target_pct']
                
                if sl_mode == "FLAT_1PCT":
                    sl_dist = entry_price * 0.01
                elif sl_mode == "SECTOR_REALISTIC":
                    sl_dist = entry_price * risk_params['sl_pct']
                elif sl_mode == "RR_2_1":
                    sl_dist = target_dist / 2.0
                elif sl_mode == "ZONE":
                    # Use PriceActionEngine to find zones
                    supports, resistances = PriceActionEngine.find_support_resistance(window)
                    buffer = entry_price * 0.001 # 0.1% buffer
                    
                    if sig.direction == 'CE':
                        # Find highest support below entry
                        s_below = [s for s in supports if s['zone'][1] < entry_price]
                        if s_below:
                            sl_price = s_below[0]['zone'][0] - buffer
                            sl_dist = entry_price - sl_price
                        else:
                            sl_dist = target_dist / 2.0 # fallback
                    else: # PE
                        # Find lowest resistance above entry
                        r_above = [r for r in resistances if r['zone'][0] > entry_price]
                        if r_above:
                            sl_price = r_above[0]['zone'][1] + buffer
                            sl_dist = sl_price - entry_price
                        else:
                            sl_dist = target_dist / 2.0 # fallback
                
                # Safety Clamp: Min 0.1%, Max 5%
                sl_dist = max(entry_price * 0.001, min(entry_price * 0.05, sl_dist))
                sl_price = entry_price - sl_dist if sig.direction == 'CE' else entry_price + sl_dist
                
                active_trade = tsl_manager.create_trade(
                    symbol=symbol, direction=sig.direction, entry_price=entry_price,
                    sl_price=sl_price, original_qty=qty, strategy=sig.strategy_name
                )

    return sum(t['pnl'] for t in trades_log)

if __name__ == "__main__":
    with open("config/universe.yaml", "r") as f:
        universe = yaml.safe_load(f)['universe']
    
    test_stocks = ["HDFCBANK", "INFY", "TATASTEEL", "ADANIENT", "ITC", "RELIANCE", "BAJFINANCE"]
    modes = ["FLAT_1PCT", "SECTOR_REALISTIC", "RR_2_1", "ZONE"]
    
    results = {mode: 0.0 for mode in modes}
    
    for mode in modes:
        logger.info(f"\n>>> TESTING SL MODE: {mode}")
        mode_total = 0.0
        for s in test_stocks:
            f_path = f"data/cache/{s}_1m.csv"
            if os.path.exists(f_path):
                pnl = run_backtest(s, f_path, universe['mappings'], sl_mode=mode)
                if pnl is not None:
                    mode_total += pnl
        results[mode] = mode_total
        logger.info(f"Total PnL for {mode}: {mode_total:,.2f} INR")

    logger.info("\n" + "="*40)
    logger.info("FINAL COMPARISON (60 Days, 7 Stocks)")
    logger.info("="*40)
    for mode, total in results.items():
        logger.info(f"{mode:18}: {total:,.2f} INR")
    logger.info("="*40)
