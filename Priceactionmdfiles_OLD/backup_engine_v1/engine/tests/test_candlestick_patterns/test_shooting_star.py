"""Tests for Shooting Star"""
import pytest
import pandas as pd
from engine.candlestick_patterns.shooting_star import ShootingStar
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return ShootingStar()


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
def sample_shooting_star_df():
    """Create a DataFrame showing a valid Shooting Star pattern."""
    # Uptrend
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
    full_prices = [100] * 20 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p + 1 for p in full_prices]
    
    # Last candle: Shooting Star
    # Open 121, Close 120 (Bearish body size 1.0)
    # Low 119.9 (Lower wick 0.1)
    # High 124.0 (Upper wick 3.0. 3x body size).
    opens[-1] = 121
    closes[-1] = 120
    lows[-1] = 119.9
    highs[-1] = 124.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Shooting Star"

    def test_detect_returns_list(self, strategy, sample_shooting_star_df):
        result = strategy.detect(sample_shooting_star_df)
        assert isinstance(result, list)


class TestDetection:
    def test_shooting_star_detection(self, strategy, sample_shooting_star_df):
        signals = strategy.detect(sample_shooting_star_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH

    def test_no_uptrend_no_detection(self, strategy):
        # Downtrend
        prices = [120, 118, 116, 114, 112, 110]
        full_prices = [120] * 20 + prices
        opens = [p + 1 for p in full_prices]
        closes = [p for p in full_prices]
        
        # Shooting Star at end of downtrend (should NOT trigger)
        opens[-1] = 111
        closes[-1] = 110
        lows = [p - 0.1 for p in closes]
        highs = [p + 3.0 for p in opens]
        df = create_ohlcv(opens, highs, lows, closes)
        
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_wick_too_short_no_detection(self, strategy):
        # Uptrend
        prices = [100, 102, 104, 106, 108, 110]
        full_prices = [100] * 20 + prices
        opens = [p for p in full_prices]
        closes = [p + 1 for p in full_prices]
        
        # Short wick (1x body)
        opens[-1] = 111
        closes[-1] = 112
        lows = [p - 0.1 for p in opens]
        highs = [p + 1.0 for p in closes]
        df = create_ohlcv(opens, highs, lows, closes)
        
        signals = strategy.detect(df)
        assert len(signals) == 0
