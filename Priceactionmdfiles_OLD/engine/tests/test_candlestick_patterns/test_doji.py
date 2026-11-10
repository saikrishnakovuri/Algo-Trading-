"""Tests for Doji"""
import pytest
import pandas as pd
from engine.candlestick_patterns.doji import Doji
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return Doji()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_standard_doji_df():
    """Create a DataFrame showing a Standard Doji."""
    prices = [100] * 30
    opens = prices[:-1] + [105.0]
    closes = prices[:-1] + [105.1]
    highs = [p + 2 for p in opens]
    lows = [p - 2 for p in opens]
    # Body = 0.1, Range = 4. 0.1 / 4 = 0.025 (<= 0.1)
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_dragonfly_doji_df():
    """Create a DataFrame showing a Dragonfly Doji."""
    prices = [100] * 30
    opens = prices[:-1] + [105.0]
    closes = prices[:-1] + [105.05]
    highs = [p + 0.1 for p in opens]
    lows = [p - 3.0 for p in opens]
    # Body = 0.05, Range = 3.1. 
    # Upper Wick = 0.05, Lower Wick = 3.0.
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_gravestone_doji_df():
    """Create a DataFrame showing a Gravestone Doji."""
    prices = [100] * 30
    opens = prices[:-1] + [105.0]
    closes = prices[:-1] + [104.95]
    highs = [p + 3.0 for p in opens]
    lows = [p - 0.1 for p in opens]
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Doji"

    def test_detect_returns_list(self, strategy, sample_standard_doji_df):
        result = strategy.detect(sample_standard_doji_df)
        assert isinstance(result, list)


class TestDetection:
    def test_standard_doji(self, strategy, sample_standard_doji_df):
        signals = strategy.detect(sample_standard_doji_df)
        assert len(signals) > 0
        assert "Standard" in signals[0].reasoning

    def test_dragonfly_doji(self, strategy, sample_dragonfly_doji_df):
        signals = strategy.detect(sample_dragonfly_doji_df)
        assert len(signals) > 0
        assert "Dragonfly" in signals[0].reasoning
        assert signals[0].market_bias == MarketBias.BULLISH

    def test_gravestone_doji(self, strategy, sample_gravestone_doji_df):
        signals = strategy.detect(sample_gravestone_doji_df)
        assert len(signals) > 0
        assert "Gravestone" in signals[0].reasoning
        assert signals[0].market_bias == MarketBias.BEARISH

    def test_non_doji(self, strategy):
        # Large body
        df = create_ohlcv([100]*30, [110]*30, [90]*30, [108]*30)
        signals = strategy.detect(df)
        assert len(signals) == 0
