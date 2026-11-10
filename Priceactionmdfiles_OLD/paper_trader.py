"""
PAPER TRADER - Edge Monitor Validated Config
=============================================
Runs the UnifiedStrategyEngine using the FINAL_PRODUCTION_CONFIG.json.

Usage:
    python paper_trader.py
"""

import pandas as pd
import json
import os
import time
from datetime import datetime
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

CONFIG_PATH = 'pipeline/results/FINAL_PRODUCTION_CONFIG.json'
DATA_FILE = "../data/nifty50_5m.csv" # Replace with live data fetcher in actual live environment

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: Config not found at {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_paper_trading(config):
    print("Initializing Unified Strategy Engine...")
    engine = UnifiedStrategyEngine()
    
    # In a real environment, you would loop and fetch the latest 5m candle here.
    # For local paper testing, we will simulate receiving the last 200 candles.
    print(f"Loading recent market data from {DATA_FILE}...")
    try:
        df = pd.read_csv(DATA_FILE)
        df.index = pd.to_datetime(df['Datetime'])
        df.columns = [c.lower() for c in df.columns]
        
        # Take the most recent 200 bars to simulate "current" market state
        current_window = df.tail(200)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    print("="*60)
    print(f"  PAPER TRADING SIMULATOR (Using {config['name']} v{config['version']})")
    print("="*60)
    
    current_time = current_window.index[-1]
    day_of_week = current_time.strftime('%A')
    hour = current_time.hour
    
    print(f"Current Market Time: {current_time} ({day_of_week})")
    
    # 1. Day Filter
    if day_of_week not in config['allowed_days']:
        print(f"→ SKIPPING: {day_of_week} is not in allowed days {config['allowed_days']}")
        return
        
    # 2. Hour Filter
    if hour not in config['allowed_hours']:
        print(f"→ SKIPPING: {hour}:00 is not in allowed hours {config['allowed_hours']}")
        return

    # 3. Detect Signals
    print("\nScanning for signals...")
    signals = engine.get_signals(current_window, backtest_mode=False) # backtest_mode=False for live
    
    if not signals:
        print("→ No signals detected on the current bar.")
        return
        
    # 4. Filter by Surviving Strategies
    valid_signals = [s for s in signals if s.strategy_name in config['strategies']]
    
    if not valid_signals:
        print(f"→ Signals detected, but none are from surviving strategies: {config['strategies']}")
        return
        
    # 5. Execute Trade based on Best Signal
    best_sig = max(valid_signals, key=lambda x: x.confidence)
    direction = 'CALL (CE)' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'PUT (PE)'
    
    print("\n" + "★"*60)
    print("  PAPER TRADE TRIGGERED")
    print("★"*60)
    print(f"  Strategy:    {best_sig.strategy_name}")
    print(f"  Direction:   {direction}")
    print(f"  Confidence:  {best_sig.confidence:.2f}")
    print(f"  Reasoning:   {best_sig.reasoning}")
    
    # 6. Apply Kelly-Optimal Risk
    capital = config['capital']
    risk_pct = config['risk_pct']
    risk_amt = capital * risk_pct
    
    # Calculate ATR for SL distance
    atr = (current_window['high'] - current_window['low']).tail(14).mean()
    sl_mult = 2.0  # From WIDE_3R or config
    sl_dist = atr * sl_mult
    
    position_size = int(risk_amt / sl_dist) if sl_dist > 0 else 0
    
    print("\n  [RISK MANAGEMENT]")
    print(f"  Suggested Risk: {risk_pct*100}% (₹{risk_amt:,.2f})")
    print(f"  SL Distance:    {sl_dist:.2f} points ({sl_mult}x ATR)")
    print(f"  Position Size:  {position_size} units")
    print("="*60)


if __name__ == "__main__":
    cfg = load_config()
    if cfg:
        run_paper_trading(cfg)
