import os
import pandas as pd
from backtest_engine import BacktestEngine
from datetime import datetime
import logging

# Configuration
DATA_DIR = "data/universe_10d"
TODAY = "2026-04-30"
INITIAL_CAPITAL = 1000000

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Forensic")

def run_forensic():
    print("="*60)
    print(f"      FORENSIC BACKTEST: {TODAY} (ZERO LATENCY)")
    print("="*60)
    
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    
    if not files:
        print("No data files found in universe_10d.")
        return

    print(f"Analyzing {len(files)} symbols for today's session...")
    
    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    
    # Run backtest for today specifically
    # Massively increased step_size to 1 (every bar) for high-fidelity signal catching
    trades = engine.run_massive_backtest_v2(
        files, 
        start_date=TODAY, 
        end_date=TODAY,
        step_size=1
    )
    
    if not trades:
        print("\nNo trades were triggered today even with zero latency.")
        return

    stats = engine.calculate_performance(trades)
    
    print("\n" + "="*40)
    print("      FORENSIC RESULTS (TODAY)")
    print("="*40)
    print(f"Total Trades:      {stats['Total Trades']}")
    print(f"Wins:              {stats['Wins']}")
    print(f"Losses:            {stats['Losses']}")
    print(f"Win Rate %:        {stats['Win Rate %']}%")
    print(f"Total Profit:      {stats['Total Profit']:.2f} INR")
    print(f"RR Ratio:          {stats['RR Ratio']:.2f}")
    print(f"Max Drawdown:      {stats['Max Drawdown']:.2f} INR")
    print("="*40)
    
    # Compare to Live session (approx -4500)
    live_pnl = -4485.32
    variance = stats['Total Profit'] - live_pnl
    
    print(f"\nLATENCY COST ANALYSIS:")
    print(f"Actual Live P&L:  {live_pnl:+.2f} INR")
    print(f"Theoretical P&L:   {stats['Total Profit']:+.2f} INR")
    print(f"NET GAIN/LOSS FROM LATENCY: {variance:+.2f} INR")
    print("\nVERDICT: " + ("Latency was the primary killer today." if variance > 0 else "Strategy adjustment also needed."))
    print("="*60)

if __name__ == "__main__":
    run_forensic()
