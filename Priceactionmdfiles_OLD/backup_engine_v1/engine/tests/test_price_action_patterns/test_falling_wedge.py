"""Tests for Falling Wedge"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.falling_wedge import FallingWedge
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return FallingWedge()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_falling_wedge_breakout_df():
    """Create a DataFrame showing a Falling Wedge with a breakout at the end."""
    # 1. Falling Resistance (Ceiling): y = -0.4x + 200
    idx = np.arange(150)
    highs = 200 - idx * 0.4
    
    # 2. Falling Support (Floor): y = -0.2x + 150
    lows = 150 - idx * 0.2
    
    # Ensure High > Low
    highs = np.maximum(highs, lows + 5)
    
    opens = (highs + lows) / 2
    closes = [o - 0.1 for o in opens]
    
    # 3. Final candle: Breakout
    # expected_high_at_149 = 200 - 149*0.4 = 140.4
    closes[149] = 152.0
    opens[149] = 140.0
    highs[149] = 152.5
    lows[149] = 139.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Falling Wedge"

    def test_detect_returns_list(self, strategy, sample_falling_wedge_breakout_df):
        result = strategy.detect(sample_falling_wedge_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_falling_wedge_breakout(self, strategy, sample_falling_wedge_breakout_df):
        signals = strategy.detect(sample_falling_wedge_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
