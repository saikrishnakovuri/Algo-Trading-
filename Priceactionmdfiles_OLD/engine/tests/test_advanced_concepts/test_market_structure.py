"""Tests for Market Structure"""
import pytest
import pandas as pd
import numpy as np
from engine.advanced_concepts.market_structure import MarketStructure
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return MarketStructure()


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
    # Current Close: 125 (BOS)
    prices = [
        100, 102, 105, 108, 110, 108, 106, 105, 107, 109, 
        112, 115, 118, 120, 118, 116, 115, 117, 119, 122, 125
    ]
    # Expand to meet required_candles (100)
    full_prices = [100] * 80 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = full_prices
    closes = [p + 0.5 for p in full_prices]
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_bearish_df():
    """Create a DataFrame showing LL and LH."""
    # Swing 1 Low: 190, Swing 1 High: 195
    # Swing 2 Low: 180, Swing 2 High: 185
    # Current Close: 175 (BOS)
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


@pytest.fixture
def sample_flat_df():
    """Create a flat/no-pattern DataFrame."""
    prices = [100] * 110
    highs = [101] * 110
    lows = [99] * 110
    opens = [100] * 110
    closes = [100] * 110
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Market Structure"
        assert strategy.category == "advanced_concept"

    def test_detect_returns_list(self, strategy, sample_flat_df):
        result = strategy.detect(sample_flat_df)
        assert isinstance(result, list)

    def test_handles_empty_df(self, strategy):
        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        result = strategy.detect(empty_df)
        assert result == []


class TestDetection:
    def test_bullish_detection(self, strategy, sample_bullish_df):
        signals = strategy.detect(sample_bullish_df)
        assert len(signals) > 0
        # Should have a BUY signal because current price (125) > last HH (120)
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)

    def test_bearish_detection(self, strategy, sample_bearish_df):
        signals = strategy.detect(sample_bearish_df)
        assert len(signals) > 0
        # Should have a SELL signal because current price (175) < last LL (180)
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)

    def test_confidence_range(self, strategy, sample_bullish_df):
        signals = strategy.detect(sample_bullish_df)
        for s in signals:
            assert 0.0 <= s.confidence <= 1.0


class TestEdgeCases:
    def test_flat_market(self, strategy, sample_flat_df):
        signals = strategy.detect(sample_flat_df)
        # Should return empty or HOLD since no clear swings are formed in a perfectly flat market
        assert len(signals) == 0 or all(s.signal_type == SignalType.HOLD for s in signals)

    def test_insufficient_data(self, strategy):
        small_df = pd.DataFrame({
            'open': [100], 'high': [101], 'low': [99],
            'close': [100.5], 'volume': [1000]
        })
        result = strategy.detect(small_df)
        assert result == []
