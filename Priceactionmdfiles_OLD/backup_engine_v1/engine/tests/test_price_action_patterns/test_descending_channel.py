"""Tests for Descending Channel"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.descending_channel import DescendingChannel
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return DescendingChannel()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_descending_channel_resistance_df():
    """Create a DataFrame showing a Descending Channel with price near resistance."""
    # 1. Falling Highs Ceiling: y = -0.2x + 200
    idx = np.arange(150)
    highs = 200 - idx * 0.2
    
    # 2. Falling Lows Floor: y = -0.2x + 180
    lows = highs - 10.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o - 0.1 for o in opens]
    
    # 3. Final candle: Near Resistance at end (idx 149)
    # expected_high_at_149 = 200 - 149*0.2 = 200 - 29.8 = 170.2
    # expected_low_at_149 = 160.2
    # Price 168 should be near resistance (40% of 10 is 4. Price must be > 170.2 - 4 = 166.2)
    closes[-1] = 168.0
    opens[-1] = 169.0
    highs[-1] = 170.0
    lows[-1] = 160.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Descending Channel"

    def test_detect_returns_list(self, strategy, sample_descending_channel_resistance_df):
        result = strategy.detect(sample_descending_channel_resistance_df)
        assert isinstance(result, list)


class TestDetection:
    def test_descending_channel_resistance_sell(self, strategy, sample_descending_channel_resistance_df):
        signals = strategy.detect(sample_descending_channel_resistance_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
