import os
import pandas as pd
import numpy as np
import yaml
import logging
import glob
from datetime import datetime, time
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.price_action_engine import PriceActionEngine
from modules.trailing_sl_manager import TrailingSLManager, ManagedTrade

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('grand_backtest')

# 1. NEW EXCEL TABLE MAPPINGS (for SECTOR_REALISTIC)
STOCK_RISK_MAP = {
    "HDFCBANK": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "ICICIBANK": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "AXISBANK": {"target_pct": 0.013, "sl_pct": 0.007, "aggr_target": 0.020},
    "KOTAKBANK": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
    "SBIN": {"target_pct": 0.015, "sl_pct": 0.008, "aggr_target": 0.025},
    "INFY": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
    "TCS": {"target_pct": 0.009, "sl_pct": 0.005, "aggr_target": 0.014},
    "WIPRO": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
    "HCLTECH": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
    "TECHM": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "RELIANCE": {"target_pct": 0.015, "sl_pct": 0.008, "aggr_target": 0.025},
    "ONGC": {"target_pct": 0.013, "sl_pct": 0.007, "aggr_target": 0.020},
    "BPCL": {"target_pct": 0.013, "sl_pct": 0.007, "aggr_target": 0.020},
    "COALINDIA": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
    "TATAMOTORS": {"target_pct": 0.018, "sl_pct": 0.009, "aggr_target": 0.030},
    "MARUTI": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "M&M": {"target_pct": 0.013, "sl_pct": 0.007, "aggr_target": 0.020},
    "EICHERMOT": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "ADANIENT": {"target_pct": 0.025, "sl_pct": 0.012, "aggr_target": 0.040},
    "ADANIPORTS": {"target_pct": 0.020, "sl_pct": 0.010, "aggr_target": 0.030},
    "BAJFINANCE": {"target_pct": 0.022, "sl_pct": 0.012, "aggr_target": 0.035},
    "TATASTEEL": {"target_pct": 0.020, "sl_pct": 0.010, "aggr_target": 0.030},
    "JSWSTEEL": {"target_pct": 0.020, "sl_pct": 0.010, "aggr_target": 0.030},
    "HINDALCO": {"target_pct": 0.015, "sl_pct": 0.008, "aggr_target": 0.025},
    "ITC": {"target_pct": 0.008, "sl_pct": 0.004, "aggr_target": 0.012},
    "HINDUNILVR": {"target_pct": 0.007, "sl_pct": 0.004, "aggr_target": 0.010},
    "NESTLEIND": {"target_pct": 0.006, "sl_pct": 0.003, "aggr_target": 0.010},
    "LT": {"target_pct": 0.013, "sl_pct": 0.007, "aggr_target": 0.020},
    "ULTRACEMCO": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "GRASIM": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "SUNPHARMA": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "DRREDDY": {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018},
    "CIPLA": {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015},
}

# 2. PRICE-BASED ABSOLUTE LADDER (Target Strat 2 fallback)
def get_price_ladder(price):
    if price <= 50: return 0.45, 0.225
    if price <= 100: return 1.25, 0.65
    if price <= 150: return 1.75, 1.0
    if price <= 200: return 2.5, 1.25
    if price <= 250: return 3.5, 1.75
    if price <= 300: return 4.5, 2.25
    if price <= 350: return 5.0, 2.5
    if price <= 400: return 6.0, 3.0
    if price <= 450: return 7.0, 3.5
    if price <= 500: return 8.0, 4.25
    if price <= 550: return 9.0, 4.5
    if price <= 600: return 10.0, 5.25
    if price <= 650: return 11.0, 5.5
    if price <= 700: return 11.5, 6.0
    if price <= 750: return 12.5, 7.0
    if price <= 800: return 13.5, 7.0
    if price <= 850: return 14.0, 7.5
    if price <= 900: return 15.0, 8.5
    if price <= 950: return 16.0, 8.5
    if price <= 1000: return 17.5, 10.0
    return price * 0.018, price * 0.009 # Fallback > 1000

def get_risk_params(symbol, price):
    if symbol in STOCK_RISK_MAP:
        return STOCK_RISK_MAP[symbol]
    if price < 100: return {"target_pct": 0.010, "sl_pct": 0.005, "aggr_target": 0.015}
    elif price < 300: return {"target_pct": 0.012, "sl_pct": 0.006, "aggr_target": 0.018}
    elif price < 600: return {"target_pct": 0.015, "sl_pct": 0.007, "aggr_target": 0.022}
    else: return {"target_pct": 0.018, "sl_pct": 0.009, "aggr_target": 0.027}

def run_grand_backtest(symbol, file_path, sl_mode, target_mode):
    try:
        df_raw = pd.read_csv(file_path, index_col=0, parse_dates=True)
        if df_raw.empty: return 0.0
        df = df_raw.loc['2025-12-01':'2026-02-28'].copy()
        if df.empty or len(df) < 100: return 0.0
        
        df_5m = PriceActionEngine.resample_data(df, '5min')
        df_5m['ATR'] = df_5m['High'].rolling(14).max() - df_5m['Low'].rolling(14).min() 
        df_5m['VolAvg'] = df_5m['Volume'].rolling(20).mean()
        
        df['idx_1m'] = range(len(df))
        m1_indices = []
        for ts in df_5m.index:
            start_ts = ts - pd.Timedelta(minutes=4)
            s_idx = df.index.searchsorted(start_ts)
            e_idx = df.index.searchsorted(ts, side='right')
            m1_indices.append((s_idx, e_idx))

        sel = StrategySelector()
        sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
        sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
        
        tsl_config = {
            'partial_exits': [{'r_multiple': 1.0, 'exit_pct': 20}, {'r_multiple': 1.5, 'exit_pct': 20},
                            {'r_multiple': 2.0, 'exit_pct': 20}, {'r_multiple': 2.5, 'exit_pct': 20},
                            {'r_multiple': 3.0, 'exit_pct': 20}]
        }
        tsl_manager = TrailingSLManager(config=tsl_config)
        
        trades_log = []
        active_trade = None
        fixed_capital = 100000.0
        df_values = df[['High', 'Low', 'Close']].values
        
        for i in range(100, len(df_5m)):
            current_ts = df_5m.index[i]
            current_time = current_ts.time()
            if current_time < time(9, 20) or current_time > time(15, 25): continue
            
            if active_trade:
                s_idx, e_idx = m1_indices[i]
                for idx in range(s_idx, e_idx):
                    h, l, c = df_values[idx]
                    if target_mode == "PRICE_LADDER_25_75" and active_trade.entry_price >= 1000:
                        r_val = abs(active_trade.entry_price - active_trade.original_sl)
                        targets = [active_trade.entry_price + (j * r_val) if active_trade.direction == 'CE' 
                                else active_trade.entry_price - (j * r_val) for j in [2.0, 3.0, 4.0, 5.0, 6.0]]
                        
                        if 0 not in active_trade.targets_hit:
                            t1 = targets[0]
                            hit = (h >= t1) if active_trade.direction == 'CE' else (l <= t1)
                            if hit:
                                pnl = (t1 - active_trade.entry_price) * (active_trade.original_qty * 0.25)
                                if active_trade.direction == 'PE': pnl = -pnl
                                trades_log.append({'pnl': pnl})
                                active_trade.remaining_qty = int(active_trade.original_qty * 0.75)
                                active_trade.targets_hit.append(0)
                                active_trade.current_sl = active_trade.entry_price
                        
                        for tidx in range(1, len(targets)):
                            if tidx in active_trade.targets_hit: continue
                            t_price = targets[tidx]
                            hit = (h >= t_price) if active_trade.direction == 'CE' else (l <= t_price)
                            if hit:
                                active_trade.targets_hit.append(tidx)
                                active_trade.current_sl = targets[tidx-1]
                        
                        hit_sl = (l <= active_trade.current_sl) if active_trade.direction == 'CE' else (h >= active_trade.current_sl)
                        if hit_sl:
                            pnl = (active_trade.current_sl - active_trade.entry_price) * active_trade.remaining_qty
                            if active_trade.direction == 'PE': pnl = -pnl
                            trades_log.append({'pnl': pnl})
                            active_trade.is_closed = True; active_trade = None; break
                    else:
                        events = tsl_manager.check_exits(active_trade, h, l, c)
                        for ev in events: trades_log.append({'pnl': ev['pnl']})
                        if active_trade.is_closed: active_trade = None; break
                
                if active_trade and current_time >= time(15, 20):
                    pnl = (df_5m['Close'].iloc[i] - active_trade.entry_price) * active_trade.remaining_qty
                    if active_trade.direction == 'PE': pnl = -pnl
                    trades_log.append({'pnl': pnl}); active_trade = None

            if not active_trade and current_time < time(14, 30):
                row_5m = df_5m.iloc[i]
                if row_5m['VolAvg'] > 0 and row_5m['Volume'] < row_5m['VolAvg']: continue
                window = df_5m.iloc[i-100:i+1]
                sig = sel.select_best(window, symbol)
                
                if sig and sig.confidence_pct >= 60:
                    entry_price = sig.entry
                    risk_params = get_risk_params(symbol, entry_price)
                    day_range = (window['High'].tail(50).max() - window['Low'].tail(50).min()) / entry_price * 100
                    vol_mult = 1.2 if day_range > 1.5 else 0.7 if day_range < 0.7 else 1.0
                    qty = int(fixed_capital / entry_price)
                    
                    if target_mode == "SECTOR_GRADUATED":
                        target_dist = entry_price * risk_params['target_pct'] * vol_mult * (1.2 if sig.confidence_pct >= 75 else 1.0)
                    elif target_mode == "PRICE_LADDER_25_75":
                        target_dist = get_price_ladder(entry_price)[0] if entry_price < 1000 else entry_price * risk_params['target_pct'] * vol_mult
                    elif target_mode == "ATR_REALISTIC":
                        target_dist = (row_5m['ATR'] if not np.isnan(row_5m['ATR']) else entry_price * 0.01) * 0.5
                    
                    if sl_mode == "FLAT_1PCT": sl_dist = entry_price * 0.01
                    elif sl_mode == "SECTOR_REALISTIC":
                        sl_dist = (get_price_ladder(entry_price)[1] if target_mode == "PRICE_LADDER_25_75" and entry_price < 1000 
                                else entry_price * risk_params['sl_pct'])
                    elif sl_mode == "RR_2_1": sl_dist = target_dist / 2.0
                    elif sl_mode == "ZONE":
                        supports, resistances = PriceActionEngine.find_support_resistance(window)
                        if sig.direction == 'CE':
                            s_below = [s for s in supports if s['zone'][1] < entry_price]
                            sl_dist = entry_price - s_below[0]['zone'][0] if s_below else target_dist/2.0
                        else:
                            r_above = [r for r in resistances if r['zone'][0] > entry_price]
                            sl_dist = r_above[0]['zone'][1] - entry_price if r_above else target_dist/2.0
                    
                    sl_dist = max(entry_price * 0.001, min(entry_price * 0.05, sl_dist))
                    sl_price = entry_price - sl_dist if sig.direction == 'CE' else entry_price + sl_dist
                    
                    active_trade = tsl_manager.create_trade(symbol, sig.direction, entry_price, sl_price, qty, sig.strategy_name, start_time=current_ts)
                    if target_mode != "PRICE_LADDER_25_75" or entry_price < 1000:
                        r_unit = target_dist / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 1.0
                        active_trade.custom_partials = [{'r_multiple': r_unit * m, 'exit_pct': 20} for m in [1.0, 1.5, 2.0, 2.5, 3.0]]
        
        return sum(t['pnl'] for t in trades_log)
    except Exception as e:
        import traceback
        logger.error(f"Error in backtest for {symbol}: {e}\n{traceback.format_exc()}")
        return 0.0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sl_mode", type=str, choices=["FLAT_1PCT", "SECTOR_REALISTIC", "RR_2_1", "ZONE"])
    parser.add_argument("--target_mode", type=str, choices=["SECTOR_GRADUATED", "PRICE_LADDER_25_75", "ATR_REALISTIC"])
    args = parser.parse_args()

    data_dir = "data/angel_historical"
    files = glob.glob(f"{data_dir}/*_1m.csv")
    stocks = []
    for f in files:
        s = os.path.basename(f).replace("_1m.csv", "")
        if s not in stocks and s not in ["banknifty", "indiavix", "nifty50", "indiavix", "niftybank", "banknifty_1m", "nifty50_1m"]:
            stocks.append(s)
    
    if args.sl_mode and args.target_mode:
        combo = f"{args.sl_mode} x {args.target_mode}"
        logger.info(f"\n>>> TESTING: {combo}")
        total = 0.0
        for s in stocks:
            f_path = os.path.join(data_dir, f"{s}_1m.csv")
            total += run_grand_backtest(s, f_path, args.sl_mode, args.target_mode)
        logger.info(f"FINAL_RESULT|{combo}|{total}")
    else:
        print("Please provide --sl_mode and --target_mode")
