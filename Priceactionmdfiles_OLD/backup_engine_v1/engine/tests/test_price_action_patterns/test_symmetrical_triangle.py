"""Tests for Symmetrical Triangle"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.symmetrical_triangle import SymmetricalTriangle
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return SymmetricalTriangle()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_symmetrical_triangle_breakout_df():
    """Create a DataFrame showing a Symmetrical Triangle with a breakout."""
    # 1. Falling Resistance: y = -0.2x + 150
    idx = np.arange(150)
    highs = 150 - idx * 0.2
    
    # 2. Rising Support: y = 0.2x + 50
    lows = 50 + idx * 0.2
    
    # Ensure High > Low (converge at idx ~ 250)
    highs = np.maximum(highs, lows + 5)
    
    opens = (highs + lows) / 2
    closes = [o + 0.1 for o in opens]
    
    # 3. Final candle: Breakout above resistance
    # expected_high_at_149 = 150 - 149*0.2 = 120.2
    closes[149] = 130.0
    opens[149] = 120.0
    highs[149] = 131.0
    lows[149] = 119.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Symmetrical Triangle"

    def test_detect_returns_list(self, strategy, sample_symmetrical_triangle_breakout_df):
        result = strategy.detect(sample_symmetrical_triangle_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_symmetrical_triangle_breakout(self, strategy, sample_symmetrical_triangle_breakout_df):
        signals = strategy.detect(sample_symmetrical_triangle_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
