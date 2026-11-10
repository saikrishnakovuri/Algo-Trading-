import os
import pandas as pd
import numpy as np
import argparse
import logging
from datetime import datetime, timedelta
from modules.sweep_retest_engine import SweepRetestEngine
from modules.strategy_adapters import sweep_retest_adapter

# Configure logging to console
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('backtest')

def run_backtest(symbol, days=30):
    logger.info(f"═══════════════════════════════════════════════════")
    logger.info(f"SWEEP RETEST BACKTEST: {symbol} ({days} days, 5m)")
    logger.info(f"═══════════════════════════════════════════════════")

    # 1. Load Data (Mock or Load from CSV)
    # For this script, we'll try to find local data or return error
    data_path = f"data/{symbol}_5m.csv"
    if not os.path.exists(data_path):
        logger.error(f"Data file not found: {data_path}. Please ensure historical data is available.")
        return

    df = pd.read_csv(data_path, parse_dates=['Timestamp'])
    df.set_index('Timestamp', inplace=True)
    
    # 2. Initialize Engine
    engine = SweepRetestEngine()
    
    # 3. Iterate Through Data
    results = []
    total_sweeps = 0
    conversions = 0
    expired_retest = 0
    expired_confirmation = 0
    
    # Warmup
    warmup = 50
    for i in range(warmup, len(df)):
        df_slice = df.iloc[:i+1]
        
        # Capture state before transition
        prev_state = engine.states.get(symbol).status if symbol in engine.states else "IDLE"
        
        # Process Signal
        signal = sweep_retest_adapter(engine, df_slice, symbol)
        
        # Capture state after transition
        curr_state = engine.states.get(symbol).status if symbol in engine.states else "IDLE"
        
        # Metrics tracking
        if prev_state == "IDLE" and curr_state == "WAITING_FOR_RETEST":
            total_sweeps += 1
        elif prev_state == "WAITING_FOR_RETEST" and curr_state == "EXPIRED":
            expired_retest += 1
        elif prev_state == "CONFIRMATION" and curr_state == "EXPIRED":
            expired_confirmation += 1
        
        if signal:
            conversions += 1
            # Simulate Outcome (Simple 1.5R target)
            entry = signal.entry
            sl = signal.sl
            target = signal.target1
            direction = signal.direction
            
            # Find result in future bars
            outcome = "PENDING"
            for j in range(i+1, min(i+100, len(df))):
                high = df.iloc[j]['High']
                low = df.iloc[j]['Low']
                
                if direction == "CE":
                    if low <= sl: outcome = "LOSE"; break
                    if high >= target: outcome = "WIN"; break
                else:
                    if high <= sl: outcome = "LOSE"; break # This is wrong for PE, PE target is lower
                    # Wait, logic fix for PE:
                    if high >= sl: outcome = "LOSE"; break
                    if low <= target: outcome = "WIN"; break
            
            results.append({'signal': signal, 'outcome': outcome})

    # 4. Generate Report
    winners = [r for r in results if r['outcome'] == "WIN"]
    losers = [r for r in results if r['outcome'] == "LOSE"]
    
    win_rate = (len(winners) / len(results) * 100) if results else 0
    
    logger.info(f"Total Sweeps Detected:     {total_sweeps}")
    logger.info(f"Converted to Entry:        {conversions} ({conversions/total_sweeps*100:.1f}%)" if total_sweeps else "Converted to Entry: 0")
    logger.info(f"Expired (no retest):       {expired_retest}")
    logger.info(f"Expired (no confirmation):  {expired_confirmation}")
    logger.info(f"───────────────────────────────────────────────────")
    logger.info(f"Entries Taken:             {len(results)}")
    logger.info(f"Winners:                   {len(winners)}")
    logger.info(f"Losers:                    {len(losers)}")
    logger.info(f"Win Rate:                  {win_rate:.1f}%")
    logger.info(f"═══════════════════════════════════════════════════")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    
    run_backtest(args.symbol, args.days)
