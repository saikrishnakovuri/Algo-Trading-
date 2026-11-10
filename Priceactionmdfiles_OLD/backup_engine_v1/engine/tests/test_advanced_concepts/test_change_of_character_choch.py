"""Tests for Change of Character (CHOCH)"""
import pytest
import pandas as pd
from engine.advanced_concepts.change_of_character_choch import ChangeOfCharacter
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return ChangeOfCharacter()


def create_ohlcv(opens, highs, lows, closes, volumes=None):
    if volumes is None:
        volumes = [1000] * len(opens)
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


@pytest.fixture
def sample_bullish_choch_df():
    """Create a DataFrame showing a Bullish CHOCH."""
    # Bearish Trend: LH1=185, LH2=175
    # Current Close breaks 175
    prices = [190, 188, 185, 182, 180, 182, 185, 182, 180, 178, 175, 172, 170, 172, 175, 172, 170, 172, 174, 180]
    full_prices = [190] * 80 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p - 1 for p in full_prices]
    opens[-1] = 174
    closes = full_prices
    volumes = [1000] * (len(full_prices) - 1) + [3000]
    return create_ohlcv(opens, highs, lows, closes, volumes)


@pytest.fixture
def sample_bearish_choch_df():
    """Create a DataFrame showing a Bearish CHOCH."""
    # Bullish Trend: HL1=115, HL2=125
    # Current Close breaks 125
    prices = [100, 105, 110, 115, 120, 118, 115, 118, 120, 122, 125, 128, 130, 128, 125, 128, 130, 128, 126, 120]
    full_prices = [100] * 80 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p + 1 for p in full_prices]
    opens[-1] = 126
    closes = full_prices
    volumes = [1000] * (len(full_prices) - 1) + [3000]
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Change of Character (CHOCH)"

    def test_detect_returns_list(self, strategy, sample_bullish_choch_df):
        result = strategy.detect(sample_bullish_choch_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_choch_detection(self, strategy, sample_bullish_choch_df):
        signals = strategy.detect(sample_bullish_choch_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.STRONG_BUY
        assert signals[0].market_bias == MarketBias.BULLISH
        assert signals[0].confidence >= 0.85

    def test_bearish_choch_detection(self, strategy, sample_bearish_choch_df):
        signals = strategy.detect(sample_bearish_choch_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.STRONG_SELL
        assert signals[0].market_bias == MarketBias.BEARISH
        assert signals[0].confidence >= 0.85


class TestEdgeCases:
    def test_insufficient_data(self, strategy):
        small_df = pd.DataFrame({'open': [100], 'high': [101], 'low': [99], 'close': [100.5], 'volume': [1000]})
        result = strategy.detect(small_df)
        assert result == []
