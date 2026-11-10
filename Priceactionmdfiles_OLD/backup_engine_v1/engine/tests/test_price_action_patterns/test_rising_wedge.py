"""Tests for Rising Wedge"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.rising_wedge import RisingWedge
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return RisingWedge()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_rising_wedge_breakout_df():
    """Create a DataFrame showing a Rising Wedge with a breakdown."""
    # 1. Rising Resistance (Shallow): y = 0.2x + 100
    idx = np.arange(150)
    highs = 100 + idx * 0.2
    
    # 2. Rising Support (Steep): y = 0.4x + 60
    lows = 60 + idx * 0.4
    
    # Ensure High > Low (they converge at idx ~ 200)
    highs = np.maximum(highs, lows + 5)
    
    opens = (highs + lows) / 2
    closes = [o + 0.1 for o in opens]
    
    # 3. Final candle: Breakdown
    # expected_low_at_149 = 60 + 149*0.4 = 119.6
    closes[149] = 110.0
    opens[149] = 120.0
    highs[149] = 121.0
    lows[149] = 109.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Rising Wedge"

    def test_detect_returns_list(self, strategy, sample_rising_wedge_breakout_df):
        result = strategy.detect(sample_rising_wedge_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_rising_wedge_breakout(self, strategy, sample_rising_wedge_breakout_df):
        signals = strategy.detect(sample_rising_wedge_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
