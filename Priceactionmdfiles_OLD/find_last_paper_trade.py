import pandas as pd
import json
import os
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

CONFIG_PATH = 'pipeline/results/FINAL_PRODUCTION_CONFIG.json'
DATA_FILE = "../data/nifty50_5m.csv"

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_last_signal():
    config = load_config()
    print("Initializing Unified Strategy Engine...")
    engine = UnifiedStrategyEngine()
    
    print(f"Loading market data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    df.index = pd.to_datetime(df['Datetime'])
    df.columns = [c.lower() for c in df.columns]
    
    print("Scanning backwards to find the last valid PAPER TRADE...")
    
    # Loop backwards from the end of the dataset
    for i in range(len(df)-1, 100, -1):
        current_time = df.index[i]
        day_of_week = current_time.strftime('%A')
        hour = current_time.hour
        
        # 1. Check strict day/time filters
        if day_of_week not in config['allowed_days']:
            continue
        if hour not in config['allowed_hours']:
            continue
            
        current_window = df.iloc[i-200:i+1]
        
        # 2. Check for signals
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals:
            continue
            
        # 3. Filter by surviving strategies
        valid_signals = [s for s in signals if s.strategy_name in config['strategies']]
        if not valid_signals:
            continue
            
        # WE FOUND ONE! Let's print it.
        best_sig = max(valid_signals, key=lambda x: x.confidence)
        direction = 'CALL (CE)' if best_sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'PUT (PE)'
        
        print("\n" + "="*60)
        print(f"  PAPER TRADE FOUND AT: {current_time} ({day_of_week})")
        print("="*60)
        print(f"  Strategy:    {best_sig.strategy_name}")
        print(f"  Direction:   {direction}")
        print(f"  Confidence:  {best_sig.confidence:.2f}")
        print(f"  Reasoning:   {best_sig.reasoning}")
        
        capital = config['capital']
        risk_pct = config['risk_pct']
        risk_amt = capital * risk_pct
        
        atr = (current_window['high'] - current_window['low']).tail(14).mean()
        sl_mult = 2.0  # WIDE_3R
        sl_dist = atr * sl_mult
        position_size = int(risk_amt / sl_dist) if sl_dist > 0 else 0
        
        print("\n  [RISK MANAGEMENT]")
        print(f"  Suggested Risk: {risk_pct*100}% (₹{risk_amt:,.2f})")
        print(f"  SL Distance:    {sl_dist:.2f} points ({sl_mult}x ATR)")
        print(f"  Position Size:  {position_size} units")
        print("="*60)
        
        # Stop after finding the most recent one
        break

if __name__ == "__main__":
    test_last_signal()