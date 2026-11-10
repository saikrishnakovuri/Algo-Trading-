"""Tests for Higher High & Higher Low"""
import pytest
import pandas as pd
from engine.advanced_concepts.higher_high_higher_low import HigherHighHigherLow
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return HigherHighHigherLow()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_bullish_df():
    """Create a DataFrame showing HH and HL."""
    # Swing 1 High: 110, Swing 1 Low: 105
    # Swing 2 High: 120, Swing 2 Low: 115
    # Current Close: 125 (Breakout)
    prices = [
        100, 102, 105, 108, 110, 108, 106, 105, 107, 109, 
        112, 115, 118, 120, 118, 116, 115, 117, 119, 122, 125
    ]
    full_prices = [100] * 80 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = full_prices
    closes = [p + 0.5 for p in full_prices]
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_bearish_df():
    """Create a DataFrame showing LL and LH (should NOT trigger)."""
    prices = [
        200, 198, 195, 192, 190, 192, 194, 195, 193, 191,
        188, 185, 182, 180, 182, 184, 185, 183, 181, 178, 175
    ]
    full_prices = [200] * 80 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = full_prices
    closes = [p - 0.5 for p in full_prices]
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Higher High & Higher Low"

    def test_detect_returns_list(self, strategy, sample_bullish_df):
        result = strategy.detect(sample_bullish_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_detection(self, strategy, sample_bullish_df):
        signals = strategy.detect(sample_bullish_df)
        assert len(signals) > 0
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
        assert any(s.signal_type in [SignalType.BUY, SignalType.HOLD] for s in signals)

    def test_bearish_no_detection(self, strategy, sample_bearish_df):
        signals = strategy.detect(sample_bearish_df)
        # Should NOT return any signals for bearish structure
        assert len(signals) == 0


class TestEdgeCases:
    def test_insufficient_data(self, strategy):
        small_df = pd.DataFrame({'open': [100], 'high': [101], 'low': [99], 'close': [100.5], 'volume': [1000]})
        result = strategy.detect(small_df)
        assert result == []
