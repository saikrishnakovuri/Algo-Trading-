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
logger = logging.getLogger('potential_backtest')

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

def run_potential_backtest(symbol, file_path, vix_df, universe_map):
    logger.info(f"Backtesting {symbol}...")
    df_raw = pd.read_csv(file_path, index_col=0, parse_dates=True)
    if df_raw.empty: return None
    
    # Last 60 days
    df = df_raw.last('60D')
    df_5m = PriceActionEngine.resample_data(df, '5min')
    
    # Setup Engines
    sel = StrategySelector()
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    sel.register("MEAN_REVERSION", MeanReversionEngine(config_path="config/mean_reversion.yaml"), mean_reversion_adapter)
    
    # Custom TSL Config for this run: 25% at T1, rest trails.
    # We will handle the trailing manually in the loop since we want to test "Full Potential"
    tsl_config = {
        'enabled': True,
        'partial_exits': [
            {'r_multiple': 2.0, 'exit_pct': 25}, # Target 1 (Base Avg)
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
    
    # We'll use subsequent R-multiples for trailing
    # T1=2.0R, T2=3.0R, T3=4.0R, etc.
    
    for i in range(100, len(df_5m)):
        current_time = df_5m.index[i].time()
        if current_time < time(9, 20) or current_time > time(15, 20): continue
        
        # Pull VIX for volatility adjustment
        vix_val = 15.0 # Default
        try:
            vix_row = vix_df.loc[:df_5m.index[i]].iloc[-1]
            vix_val = vix_row['Close']
        except: pass
        
        vol_mult = 1.0
        if vix_val > 15: vol_mult = 1.3
        elif vix_val < 12: vol_mult = 0.7
        
        # 1. Check Exit
        if active_trade:
            row_1m = df.loc[df_5m.index[i-1] : df_5m.index[i]]
            for _, tick in row_1m.iterrows():
                # We need to manually handle the 25%/75% logic for "Full Potential"
                # If T1 hit, book 25% and move SL to Entry.
                # If T2 hit, move SL to T1.
                # If T3 hit, move SL to T2... and so on.
                
                # Check for subsequent targets for trailing
                r_val = abs(active_trade.entry_price - active_trade.original_sl)
                targets = [active_trade.entry_price + (j * r_val) if active_trade.direction == 'CE' 
                           else active_trade.entry_price - (j * r_val) for j in [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]]
                
                # T1 Check
                if 0 not in active_trade.targets_hit:
                    t1 = targets[0]
                    hit = (tick['High'] >= t1) if active_trade.direction == 'CE' else (tick['Low'] <= t1)
                    if hit:
                        pnl = (t1 - active_trade.entry_price) * (active_trade.original_qty * 0.25)
                        if active_trade.direction == 'PE': pnl = -pnl
                        trades_log.append({'pnl': pnl})
                        active_trade.remaining_qty = int(active_trade.original_qty * 0.75)
                        active_trade.targets_hit.append(0)
                        active_trade.current_sl = active_trade.entry_price # Move to Breakeven
                        logger.debug(f"T1 Hit for {symbol}, 25% booked, SL at Breakeven")
                
                # Subsequent Target Trailing
                for idx in range(1, len(targets)):
                    if idx in active_trade.targets_hit: continue
                    target_price = targets[idx]
                    hit = (tick['High'] >= target_price) if active_trade.direction == 'CE' else (tick['Low'] <= target_price)
                    if hit:
                        active_trade.targets_hit.append(idx)
                        active_trade.current_sl = targets[idx-1] # Move SL to previous target
                        logger.debug(f"T{idx+1} Hit for {symbol}, SL moved to T{idx}")
                
                # SL Check
                hit_sl = (tick['Low'] <= active_trade.current_sl) if active_trade.direction == 'CE' else (tick['High'] >= active_trade.current_sl)
                if hit_sl:
                    # Final Close
                    pnl = (active_trade.current_sl - active_trade.entry_price) * active_trade.remaining_qty
                    if active_trade.direction == 'PE': pnl = -pnl
                    trades_log.append({'pnl': pnl})
                    active_trade.is_closed = True
                    active_trade = None
                    break
            
            # End of day force close
            if active_trade and df_5m.index[i].time() >= time(15, 20):
                pnl = (df_5m['Close'].iloc[i] - active_trade.entry_price) * active_trade.remaining_qty
                if active_trade.direction == 'PE': pnl = -pnl
                trades_log.append({'pnl': pnl})
                active_trade = None
        
        # 2. Check Entry
        if not active_trade and current_time < time(14, 30):
            window = df_5m.iloc[i-100:i+1]
            sig = sel.select_best(window, symbol)
            
            if sig and sig.confidence_pct >= 60:
                entry_price = sig.entry
                qty = int(fixed_capital / entry_price)
                
                # Confidence Boost
                target_mult = vol_mult
                if sig.confidence_pct > 75:
                    target_mult *= 1.2
                
                # Sector Realistic SL
                sl_dist = entry_price * risk_params['sl_pct']
                sl_price = entry_price - sl_dist if sig.direction == 'CE' else entry_price + sl_dist
                
                # Create Trade
                active_trade = tsl_manager.create_trade(
                    symbol=symbol, direction=sig.direction, entry_price=entry_price,
                    sl_price=sl_price, original_qty=qty, strategy=sig.strategy_name
                )
                active_trade.confidence = sig.confidence_pct

    return sum(t['pnl'] for t in trades_log)

if __name__ == "__main__":
    with open("config/universe.yaml", "r") as f:
        universe = yaml.safe_load(f)['universe']
    
    # Load VIX
    vix_df = pd.read_csv("data/indiavix_5m.csv", index_col=0, parse_dates=True)
    
    test_stocks = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
        "BAJFINANCE", "BANKBARODA", "BHARTIARTL", "BPCL", "CIPLA", 
        "COALINDIA", "DRREDDY", "GAIL", "HCLTECH", "HDFCBANK", 
        "HINDALCO", "ICICIBANK", "INFY", "ITC", "JSWSTEEL", 
        "KOTAKBANK", "LT", "MARUTI", "NTPC", "ONGC"
    ]
    
    total_system_pnl = 0.0
    stock_count = 0
    
    logger.info(f"\n🚀 STARTING FULL POTENTIAL BACKTEST (25 STOCKS, 60 DAYS)")
    logger.info(f"Settings: Sector Realistic SL, VIX Adjusted Target, 25%@T1 + 75% Trail")
    logger.info("="*60)
    
    for s in test_stocks:
        f_path = f"data/cache/{s}_1m.csv"
        if os.path.exists(f_path):
            pnl = run_potential_backtest(s, f_path, vix_df, universe['mappings'])
            if pnl is not None:
                total_system_pnl += pnl
                stock_count += 1
                logger.info(f"  {s:12}: {pnl:,.2f} INR")
        else:
            logger.warning(f"  {s:12}: DATA NOT FOUND")

    logger.info("="*60)
    logger.info(f"FINAL SYSTEM PnL: {total_system_pnl:,.2f} INR ({stock_count} stocks)")
    logger.info("="*60)
