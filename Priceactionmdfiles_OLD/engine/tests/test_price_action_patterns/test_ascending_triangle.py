"""Tests for Ascending Triangle"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.ascending_triangle import AscendingTriangle
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return AscendingTriangle()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_ascending_triangle_breakout_df():
    """Create a DataFrame showing an Ascending Triangle with a breakout."""
    # 1. Rising Lows Floor
    idx = np.arange(150)
    lows = 100 + idx * 0.2
    
    # 2. Flat Resistance Ceiling at 140 (hit multiple times)
    highs = [min(140.0, l + 5.0) for l in lows]
    # Ensure some hit 140 exactly
    for i in range(120, 149):
        highs[i] = 140.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # 3. Final candle: Breakout
    highs[-1] = 145.0
    closes[-1] = 144.0
    opens[-1] = 141.0
    lows[-1] = 140.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Ascending Triangle"

    def test_detect_returns_list(self, strategy, sample_ascending_triangle_breakout_df):
        result = strategy.detect(sample_ascending_triangle_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_ascending_triangle_breakout(self, strategy, sample_ascending_triangle_breakout_df):
        signals = strategy.detect(sample_ascending_triangle_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
