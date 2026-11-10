"""Tests for Morning Star"""
import pytest
import pandas as pd
from engine.candlestick_patterns.morning_star import MorningStar
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return MorningStar()


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
def sample_morning_star_df():
    """Create a DataFrame showing a valid Morning Star pattern."""
    # Downtrend
    prices = [120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
    full_prices = [120] * 30 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p + 1 for p in full_prices]
    closes = [p for p in full_prices]
    
    # C1 (index -3): Open 110, Close 100 (Bearish)
    # C2 (index -2): Open 98, Close 98.5 (Small Bullish Star) - Body 0.5 < 10*0.3=3.0
    # C3 (index -1): Open 99, Close 106 (Bullish) - Midpoint of 110-100 is 105. 106 > 105.
    opens[-3] = 110
    closes[-3] = 100
    opens[-2] = 98
    closes[-2] = 98.5
    opens[-1] = 99
    closes[-1] = 106
    highs[-1] = 107
    lows[-1] = 98
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Morning Star"

    def test_detect_returns_list(self, strategy, sample_morning_star_df):
        result = strategy.detect(sample_morning_star_df)
        assert isinstance(result, list)


class TestDetection:
    def test_morning_star_detection(self, strategy, sample_morning_star_df):
        signals = strategy.detect(sample_morning_star_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].market_bias == MarketBias.BULLISH

    def test_middle_candle_too_large_no_detection(self, strategy):
        # Downtrend
        prices = [120] * 30 + [110, 108, 106]
        opens = [p + 1 for p in prices]
        closes = [p for p in prices]
        
        # C1 Bearish, C2 TOO LARGE, C3 Bullish
        opens[-3] = 110
        closes[-3] = 100 # Body 10
        opens[-2] = 98
        closes[-2] = 93 # Body 5 (> 10*0.3=3)
        opens[-1] = 93
        closes[-1] = 106 # Closes above midpoint 105
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_third_candle_weak_no_detection(self, strategy):
        # Downtrend
        prices = [120] * 30 + [110, 108, 106]
        opens = [p + 1 for p in prices]
        closes = [p for p in prices]
        
        # C1 Bearish, C2 Star, C3 fails midpoint
        opens[-3] = 110
        closes[-3] = 100 # Midpoint 105
        opens[-2] = 98
        closes[-2] = 98.5 # Star
        opens[-1] = 99
        closes[-1] = 103 # Below 105
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
