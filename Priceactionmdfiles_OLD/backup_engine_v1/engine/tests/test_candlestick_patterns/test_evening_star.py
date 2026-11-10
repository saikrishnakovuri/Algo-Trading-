"""Tests for Evening Star"""
import pytest
import pandas as pd
from engine.candlestick_patterns.evening_star import EveningStar
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return EveningStar()


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
def sample_evening_star_df():
    """Create a DataFrame showing a valid Evening Star pattern."""
    # Uptrend
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
    full_prices = [100] * 30 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p + 1 for p in full_prices]
    
    # C1 (index -3): Open 120, Close 130 (Bullish)
    # C2 (index -2): Open 132, Close 132.5 (Small Bullish Star) - Body 0.5 < 10*0.3=3.0
    # C3 (index -1): Open 132, Close 124 (Bearish) - Midpoint of 120-130 is 125. 124 < 125.
    opens[-3] = 120
    closes[-3] = 130
    opens[-2] = 132
    closes[-2] = 132.5
    opens[-1] = 132
    closes[-1] = 124
    highs[-1] = 133
    lows[-1] = 123
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Evening Star"

    def test_detect_returns_list(self, strategy, sample_evening_star_df):
        result = strategy.detect(sample_evening_star_df)
        assert isinstance(result, list)


class TestDetection:
    def test_evening_star_detection(self, strategy, sample_evening_star_df):
        signals = strategy.detect(sample_evening_star_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH

    def test_middle_candle_too_large_no_detection(self, strategy):
        # Uptrend
        prices = [100] * 30 + [110, 112, 114]
        opens = [p for p in prices]
        closes = [p + 1 for p in prices]
        
        # C1 Bullish, C2 TOO LARGE, C3 Bearish
        opens[-3] = 110
        closes[-3] = 120 # Body 10
        opens[-2] = 122
        closes[-2] = 127 # Body 5 (> 10*0.3=3)
        opens[-1] = 127
        closes[-1] = 114 # Closes below midpoint 115
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_third_candle_weak_no_detection(self, strategy):
        # Uptrend
        prices = [100] * 30 + [110, 112, 114]
        opens = [p for p in prices]
        closes = [p + 1 for p in prices]
        
        # C1 Bullish, C2 Star, C3 fails midpoint
        opens[-3] = 110
        closes[-3] = 120 # Midpoint 115
        opens[-2] = 122
        closes[-2] = 123 # Star
        opens[-1] = 123
        closes[-1] = 117 # Above 115
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
