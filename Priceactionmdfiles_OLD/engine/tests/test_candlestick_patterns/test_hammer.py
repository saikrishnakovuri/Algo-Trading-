"""Tests for Hammer"""
import pytest
import pandas as pd
from engine.candlestick_patterns.hammer import Hammer
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return Hammer()


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
def sample_hammer_df():
    """Create a DataFrame showing a valid Hammer pattern."""
    # Downtrend
    prices = [120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
    full_prices = [120] * 20 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p - 1 for p in full_prices]
    
    # Last candle: Hammer
    # Open 100, Close 101 (Bullish body size 1.0)
    # High 101.1 (Upper wick 0.1)
    # Low 97.0 (Lower wick 3.0. 3x body size).
    opens[-1] = 100
    closes[-1] = 101
    highs[-1] = 101.1
    lows[-1] = 97.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Hammer"

    def test_detect_returns_list(self, strategy, sample_hammer_df):
        result = strategy.detect(sample_hammer_df)
        assert isinstance(result, list)


class TestDetection:
    def test_hammer_detection(self, strategy, sample_hammer_df):
        signals = strategy.detect(sample_hammer_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].market_bias == MarketBias.BULLISH

    def test_no_downtrend_no_detection(self, strategy):
        # Uptrend
        prices = [100, 102, 104, 106, 108, 110]
        full_prices = [100] * 20 + prices
        opens = [p for p in full_prices]
        closes = [p + 1 for p in full_prices]
        
        # Hammer at end of uptrend (should NOT trigger)
        opens[-1] = 110
        closes[-1] = 111
        highs = [p + 0.1 for p in closes]
        lows = [p - 3.0 for p in opens]
        df = create_ohlcv(opens, highs, lows, closes)
        
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_wick_too_short_no_detection(self, strategy):
        # Downtrend
        prices = [120, 118, 116, 114, 112, 110]
        full_prices = [120] * 20 + prices
        opens = [p for p in full_prices]
        closes = [p - 1 for p in full_prices]
        
        # Short wick (1x body)
        opens[-1] = 110
        closes[-1] = 109
        highs = [p + 0.1 for p in opens]
        lows = [p - 1.0 for p in closes]
        df = create_ohlcv(opens, highs, lows, closes)
        
        signals = strategy.detect(df)
        assert len(signals) == 0
