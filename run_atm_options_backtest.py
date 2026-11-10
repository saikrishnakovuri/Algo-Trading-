import os
import pandas as pd
import numpy as np
from backtest_engine import BacktestEngine
from modules.price_action_engine import PriceActionEngine

def run_atm_options_backtest():
    initial_capital = 500000.0
    
    # Target fetched Nifty Data
    file_path = "data/nifty_index/NIFTY_Jan2026.csv"
    
    # Load and clean data
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    df.columns = [c.capitalize() for c in df.columns]
    df['high'] = df['High']
    df['low'] = df['Low']
    df['close'] = df['Close']
    df['open'] = df['Open']
    df['volume'] = df['Volume']
    
    # Engine requires list of files
    engine = BacktestEngine(initial_capital=initial_capital)
    
    print(f"Starting Nifty Index Backtest for Jan 2026...")
    
    # The current engine expects multiple files and loops through them.
    # To run on index data, we treat the index as a 'symbol' and provide it as a file list.
    trades = engine.run_massive_backtest_v2(
        files=[file_path],
        start_date="2026-01-01",
        end_date="2026-01-31"
    )
    
    # PnL simulation logic for Delta 0.5 ATM Option
    # Since the engine doesn't natively handle 0.5 delta, we adjust the output.
    # We estimate PnL: Delta * Index_Move * Multiplier (Nifty Lot Size)
    nifty_lot = 25
    total_pnl = 0
    for t in trades:
        # Simplified estimate
        # Delta 0.5: Gain/Loss = 0.5 * Index_Move * Lot_Size
        pnl_adj = t['pnl'] * 0.5 # Delta adjustment
        total_pnl += pnl_adj
        print(f"Date: {t['date']} | Type: {t['type']} | Setup: {t['setup']} | Adj PnL: {pnl_adj}")
    
    print(f"Total Adjusted PnL (ATM Delta 0.5): {total_pnl}")
    return trades

if __name__ == "__main__":
    run_atm_options_backtest()
