import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from modules.mean_reversion_engine import MeanReversionEngine
from modules.momentum_engine import MomentumBreakoutEngine
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter
from modules.strategy_selector import StrategySelector

def run_selector_diagnostic(symbol="RELIANCE"):
    mr_engine = MeanReversionEngine()
    mom_engine = MomentumBreakoutEngine()
    
    selector = StrategySelector()
    selector.register("MOMENTUM", mom_engine, momentum_adapter)
    selector.register("MEAN_REVERSION", mr_engine, mean_reversion_adapter)
    
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return

    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_raw.sort_index(inplace=True)

    periods = {
        "April 2026": ("2026-04-01", "2026-04-12"),
        "Dec 2025": ("2025-12-01", "2025-12-12")
    }

    for name, (start, end) in periods.items():
        print(f"\n--- Selector Diagnostic: {name} ---")
        start_ist = pd.Timestamp(start).tz_localize('Asia/Kolkata')
        end_ist = pd.Timestamp(end).tz_localize('Asia/Kolkata')
        warmup_start = start_ist - timedelta(days=10)
        
        df_period = df_raw[(df_raw.index >= warmup_start) & (df_raw.index <= end_ist)]
        df_5m = df_period.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        df_5m = df_5m.between_time('09:15', '15:30')
        
        stats = {
            'MR_Potential': 0,
            'MOM_Potential': 0,
            'MR_Wins': 0,
            'MOM_Wins': 0,
            'MR_Blocked_By_Conf': 0,
            'MR_Lost_To_MOM': 0
        }
        
        for i in range(50, len(df_5m)):
            ts = df_5m.index[i]
            if ts < start_ist: continue
            
            df_slice = df_5m.iloc[:i+1]
            
            mr_res = mean_reversion_adapter(mr_engine, df_slice, symbol)
            mom_res = momentum_adapter(mom_engine, df_slice, symbol)
            
            if mr_res:
                stats['MR_Potential'] += 1
                if mr_res.confidence_pct < 60:
                    stats['MR_Blocked_By_Conf'] += 1
            
            if mom_res:
                stats['MOM_Potential'] += 1
            
            best = selector.select_best(df_slice, symbol)
            if best and best.confidence_pct >= 60:
                if best.strategy_name == "MEAN_REVERSION":
                    stats['MR_Wins'] += 1
                elif best.strategy_name == "MOMENTUM":
                    stats['MOM_Wins'] += 1
                    # Check if MR also had a signal here
                    if mr_res and mr_res.confidence_pct >= 60:
                        stats['MR_Lost_To_MOM'] += 1
                        
        print(f"Stats: {stats}")
        if stats['MR_Potential'] > 0:
            print(f"MR conversion rate: {stats['MR_Wins']/stats['MR_Potential']*100:.1f}%")

if __name__ == "__main__":
    run_selector_diagnostic()
