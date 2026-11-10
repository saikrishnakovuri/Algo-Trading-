"""Tests for Descending Triangle"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.descending_triangle import DescendingTriangle
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return DescendingTriangle()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_descending_triangle_breakout_df():
    """Create a DataFrame showing a Descending Triangle with a breakdown."""
    # 1. Falling Highs Ceiling
    idx = np.arange(150)
    highs = 150 - idx * 0.2
    
    # 2. Flat Support Floor at 110 (hit multiple times)
    lows = [max(110.0, h - 5.0) for h in highs]
    # Ensure some hit 110 exactly
    for i in range(120, 149):
        lows[i] = 110.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o - 0.1 for o in opens]
    
    # 3. Final candle: Breakdown
    lows[-1] = 105.0
    closes[-1] = 106.0
    opens[-1] = 111.0
    highs[-1] = 112.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Descending Triangle"

    def test_detect_returns_list(self, strategy, sample_descending_triangle_breakout_df):
        result = strategy.detect(sample_descending_triangle_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_descending_triangle_breakout(self, strategy, sample_descending_triangle_breakout_df):
        signals = strategy.detect(sample_descending_triangle_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
