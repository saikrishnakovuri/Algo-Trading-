"""Tests for Ascending Channel"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.ascending_channel import AscendingChannel
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return AscendingChannel()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_ascending_channel_df():
    """Create a DataFrame showing a clean Ascending Channel."""
    # Prices moving up with strong oscillations
    idx = np.arange(150)
    # Slope 0.5, Amplitude 10 (Derivative min: 0.5 - 10/5 = -1.5 -> Has pullbacks)
    lows = 0.5 * idx + 98 + np.sin(idx/5) * 10
    highs = 0.5 * idx + 115 + np.sin(idx/5) * 10
    
    # Ensure High > Low
    highs = np.maximum(highs, lows + 5)
    
    opens = (highs + lows) / 2
    closes = opens + 1.0
    
    # Current Price near support at end
    # We'll manually set the last few to be near the lower boundary
    current_expected_low = 0.5 * 149 + 98 + np.sin(149/5) * 10
    closes[-1] = current_expected_low + 2.0
    opens[-1] = current_expected_low + 1.0
    lows[-1] = current_expected_low
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Ascending Channel"

    def test_detect_returns_list(self, strategy, sample_ascending_channel_df):
        result = strategy.detect(sample_ascending_channel_df)
        assert isinstance(result, list)


class TestDetection:
    def test_ascending_channel_support_buy(self, strategy, sample_ascending_channel_df):
        signals = strategy.detect(sample_ascending_channel_df)
        assert len(signals) > 0
        # Should detect BUY near support
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
