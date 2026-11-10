"""Tests for Cup and Handle"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.cup_and_handle import CupAndHandle
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return CupAndHandle()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_cup_and_handle_breakout_df():
    """Create a DataFrame showing a Cup and Handle with a breakout."""
    # 1. Lip 1 at 150 (idx 40)
    # 2. Bottom at 130 (idx 60)
    # 3. Lip 2 at 150 (idx 80)
    # 4. Handle Low at 145 (idx 90)
    # 5. Breakout at 155 (idx 100)
    
    size = 160
    full_prices = [140.0] * size
    
    # Manually build the rounded cup
    # Lip 1 to Bottom: 40 to 60
    for i, val in enumerate(np.linspace(150, 130, 21)):
        full_prices[40 + i] = val
    # Bottom to Lip 2: 60 to 80
    for i, val in enumerate(np.linspace(130, 150, 21)):
        full_prices[60 + i] = val
        
    # Handle: 80 to 95
    for i, val in enumerate(np.linspace(150, 145, 10)):
        full_prices[80 + i] = val
    for i, val in enumerate(np.linspace(145, 150, 6)):
        full_prices[90 + i] = val
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure Lip 1 and Lip 2 are peaks
    highs[40] = 150.0
    lows[40] = 149.0
    highs[39] = highs[41] = 148.0
    
    highs[80] = 150.0
    lows[80] = 149.0
    highs[79] = highs[81] = 148.0
    
    # Ensure Bottom is a trough
    lows[60] = 130.0
    highs[60] = 131.0
    lows[59] = lows[61] = 132.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Final Breakout candle
    closes[-1] = 155.0
    opens[-1] = 149.0
    highs[-1] = 155.5
    lows[-1] = 148.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Cup and Handle"

    def test_detect_returns_list(self, strategy, sample_cup_and_handle_breakout_df):
        result = strategy.detect(sample_cup_and_handle_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_cup_and_handle_breakout(self, strategy, sample_cup_and_handle_breakout_df):
        signals = strategy.detect(sample_cup_and_handle_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
