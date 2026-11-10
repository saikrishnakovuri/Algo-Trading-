
import pandas as pd
import numpy as np
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

def generate_data(size=100):
    prices = 100 + np.cumsum(np.random.randn(size))
    df = pd.DataFrame({
        'open': prices - 0.5,
        'high': prices + 1,
        'low': prices - 1,
        'close': prices,
        'volume': np.random.randint(1000, 5000, size=size)
    }, index=pd.date_range('2026-01-01', periods=size, freq='5min'))
    return df

def test():
    engine = UnifiedStrategyEngine()
    df = generate_data(200)
    print("Testing get_signals...")
    try:
        signals = engine.get_signals(df, timeframe="5m")
        print(f"Found {len(signals)} signals.")
    except Exception as e:
        print(f"Caught expected error or bug: {e}")

if __name__ == "__main__":
    test()
