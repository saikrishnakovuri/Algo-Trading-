"""Tests for Break of Structure (BOS)"""
import pytest
import pandas as pd
from engine.advanced_concepts.break_of_structure_bos import BreakOfStructure
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BreakOfStructure()


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
def sample_bullish_bos_df():
    """Create a DataFrame showing a Bullish BOS."""
    # Last HH was at 120
    # Current Close is 125 with strong displacement
    prices = [
        100, 102, 105, 108, 110, 108, 106, 105, 107, 109, 
        112, 115, 118, 120, 118, 116, 115, 117, 119, 120, 
        121, # Prev candle close below 120
        125  # Current candle close above 120 (BOS)
    ]
    full_prices = [100] * 80 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p - 2 for p in full_prices] # Making body larger for displacement
    # Adjusting current candle for displacement
    opens[-1] = 121
    closes = full_prices
    volumes = [1000] * 101 + [3000] # High volume on BOS
    return create_ohlcv(opens, highs, lows, closes, volumes)


@pytest.fixture
def sample_bearish_bos_df():
    """Create a DataFrame showing a Bearish BOS."""
    # Last LL was at 180
    # Current Close is 175 with strong displacement
    prices = [
        200, 198, 195, 192, 190, 192, 194, 195, 193, 191,
        188, 185, 182, 180, 182, 184, 185, 183, 181, 180,
        179, # Prev candle close above 180
        175  # Current candle close below 180 (BOS)
    ]
    full_prices = [200] * 80 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p + 2 for p in full_prices]
    opens[-1] = 179
    closes = full_prices
    volumes = [1000] * 101 + [3000]
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Break of Structure (BOS)"

    def test_detect_returns_list(self, strategy, sample_bullish_bos_df):
        result = strategy.detect(sample_bullish_bos_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_bos_detection(self, strategy, sample_bullish_bos_df):
        signals = strategy.detect(sample_bullish_bos_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].market_bias == MarketBias.BULLISH
        assert signals[0].confidence >= 0.8 # Due to displacement and volume

    def test_bearish_bos_detection(self, strategy, sample_bearish_bos_df):
        signals = strategy.detect(sample_bearish_bos_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH
        assert signals[0].confidence >= 0.8


class TestEdgeCases:
    def test_no_bos_no_signal(self, strategy):
        # Data that stays within structure
        prices = [100] * 110
        df = create_ohlcv(prices, [p+1 for p in prices], [p-1 for p in prices], prices)
        result = strategy.detect(df)
        assert result == []
