"""Tests for Spinning Top"""
import pytest
import pandas as pd
from engine.candlestick_patterns.spinning_top import SpinningTop
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return SpinningTop()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_spinning_top_df():
    """Create a DataFrame showing a valid Spinning Top."""
    prices = [100] * 30
    # Range = 10, Body = 1.0 (10%). Wicks = 4.5 each.
    opens = prices[:-1] + [104.5]
    closes = prices[:-1] + [105.5]
    highs = prices[:-1] + [110]
    lows = prices[:-1] + [100]
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Spinning Top"

    def test_detect_returns_list(self, strategy, sample_spinning_top_df):
        result = strategy.detect(sample_spinning_top_df)
        assert isinstance(result, list)


class TestDetection:
    def test_spinning_top_detection(self, strategy, sample_spinning_top_df):
        signals = strategy.detect(sample_spinning_top_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.HOLD
        assert signals[0].market_bias == MarketBias.NEUTRAL

    def test_asymmetrical_wicks_no_detection(self, strategy):
        # Long lower wick (Hammer-like), not balanced
        prices = [100] * 30
        opens = prices[:-1] + [109]
        closes = prices[:-1] + [110]
        highs = prices[:-1] + [110.1]
        lows = prices[:-1] + [104]
        # Range 6.1. Body 1.0. Upper 0.1. Lower 5.0. 
        # Ratio 0.1/5.0 = 0.02 (< 0.5)
        df = create_ohlcv(opens, highs, lows, closes)
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_large_body_no_detection(self, strategy):
        # Range 10, Body 5.0 (50% > 30%)
        df = create_ohlcv([100]*30, [110]*30, [100]*30, [105]*30)
        signals = strategy.detect(df)
        assert len(signals) == 0
