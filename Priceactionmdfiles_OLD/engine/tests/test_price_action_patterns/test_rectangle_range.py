"""Tests for Rectangle Range"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.rectangle_range import RectangleRange
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return RectangleRange()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_rectangle_breakout_df():
    """Create a DataFrame showing a Rectangle with a breakout."""
    size = 150
    # Range: 100 to 120
    idx = np.arange(size)
    osc = 10 * np.sin(idx/5) + 110
    
    highs = osc + 1.0
    lows = osc - 1.0
    
    # Boundary touches
    for i in [110, 120, 130, 140]: highs[i] = 120.0
    for i in [115, 125, 135, 145]: lows[i] = 100.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Breakout at end
    closes[-1] = 125.0
    opens[-1] = 120.0
    highs[-1] = 125.5
    lows[-1] = 119.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Rectangle Range"

    def test_detect_returns_list(self, strategy, sample_rectangle_breakout_df):
        result = strategy.detect(sample_rectangle_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_rectangle_breakout(self, strategy, sample_rectangle_breakout_df):
        signals = strategy.detect(sample_rectangle_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
