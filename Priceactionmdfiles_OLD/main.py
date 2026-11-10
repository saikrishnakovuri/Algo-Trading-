"""
MAIN ENTRY POINT - Integration Test for Strategy Engine
"""

import pandas as pd
import numpy as np
from engine.strategy_engine import StrategyEngine
from engine.signal import Signal

def generate_complex_market_data(size=500):
    """
    Generate synthetic data with various phases:
    1. Uptrend (0-100)
    2. Consolidation (100-200)
    3. Downtrend (200-300)
    4. Reversal (300-400)
    5. Final Breakout (400-500)
    """
    idx = np.arange(size)
    prices = np.zeros(size)
    
    # Uptrend
    prices[:100] = 100 + idx[:100] * 0.5 + np.sin(idx[:100]/5) * 5
    
    # Consolidation (Rectangle)
    prices[100:200] = 150 + np.sin(idx[100:200]/3) * 10
    
    # Downtrend
    prices[200:300] = 150 - (idx[200:300]-200) * 0.8 + np.sin(idx[200:300]/5) * 5
    
    # Reversal (Double Bottom / Wedge)
    prices[300:400] = 70 + np.sin(idx[300:400]/10) * 15
    
    # Final Breakout
    prices[400:500] = 100 + (idx[400:500]-400) * 1.5
    
    df = pd.DataFrame({
        'open': prices - 1,
        'high': prices + 2,
        'low': prices - 3,
        'close': prices,
        'volume': np.random.randint(1000, 5000, size=size)
    })
    return df

def main():
    print("Initializing Strategy Engine...")
    engine = StrategyEngine()
    print(f"Loaded {len(engine.strategies)} strategies.")
    
    print("Generating synthetic market data...")
    df = generate_complex_market_data()
    
    print("Running detection on full dataset...")
    summary = engine.get_summary(df, timeframe="15m")
    
    print("\n" + "="*50)
    print("   PRICE ACTION ENGINE SUMMARY")
    print("="*50)
    print(f"Overall Market Bias: {summary['bias']}")
    print(f"Bullish Signals:    {summary['bullish_count']}")
    print(f"Bearish Signals:    {summary['bearish_count']}")
    print("-" * 50)
    print("Top 5 Detected Patterns/Signals:")
    for i, s in enumerate(summary['top_signals'], 1):
        print(f"{i}. {s['strategy']} | {s['signal']} | Conf: {s['confidence']:.2f}")
        print(f"   Reasoning: {s['reasoning']}")
    print("="*50)
    print("\nIntegration Test COMPLETE.")

if __name__ == "__main__":
    main()
