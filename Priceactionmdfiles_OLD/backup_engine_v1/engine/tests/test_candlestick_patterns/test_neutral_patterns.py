"""Tests for Neutral Patterns"""
import pytest
import pandas as pd
from engine.candlestick_patterns.neutral_patterns import NeutralPatterns
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return NeutralPatterns()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_inside_bar_df():
    """Create a DataFrame showing an Inside Bar."""
    # Prev: High 110, Low 100
    # Current: High 108, Low 102
    prices = [100] * 30
    opens = prices[:-2] + [102, 104]
    closes = prices[:-2] + [108, 106]
    highs = prices[:-2] + [110, 108]
    lows = prices[:-2] + [100, 102]
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_spinning_top_df():
    """Create a DataFrame showing a Spinning Top."""
    prices = [100] * 30
    # Range = 10, Body = 1.0 (10% of range). Wicks = 4.5 each.
    opens = prices[:-1] + [104.5]
    closes = prices[:-1] + [105.5]
    highs = prices[:-1] + [110]
    lows = prices[:-1] + [100]
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_nr7_df():
    """Create a DataFrame showing an NR7 pattern."""
    # Last 7 ranges: 10, 10, 10, 10, 10, 10, 2
    prices = [100] * 30
    highs = [110] * 23 + [110, 110, 110, 110, 110, 110, 101]
    lows = [100] * 23 + [100, 100, 100, 100, 100, 100, 99]
    return create_ohlcv(prices, highs, lows, prices)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Neutral Patterns"

    def test_detect_returns_list(self, strategy, sample_inside_bar_df):
        result = strategy.detect(sample_inside_bar_df)
        assert isinstance(result, list)


class TestDetection:
    def test_inside_bar_detection(self, strategy, sample_inside_bar_df):
        signals = strategy.detect(sample_inside_bar_df)
        assert len(signals) > 0
        assert any("Inside Bar" in s.reasoning for s in signals)

    def test_spinning_top_detection(self, strategy, sample_spinning_top_df):
        signals = strategy.detect(sample_spinning_top_df)
        assert len(signals) > 0
        assert any("Spinning Top" in s.reasoning for s in signals)

    def test_nr7_detection(self, strategy, sample_nr7_df):
        signals = strategy.detect(sample_nr7_df)
        assert len(signals) > 0
        assert any("NR7" in s.reasoning for s in signals)
