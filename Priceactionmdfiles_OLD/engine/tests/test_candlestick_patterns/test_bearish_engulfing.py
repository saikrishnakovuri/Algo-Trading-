"""Tests for Bearish Engulfing"""
import pytest
import pandas as pd
from engine.candlestick_patterns.bearish_engulfing import BearishEngulfing
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BearishEngulfing()


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
def sample_bearish_engulfing_df():
    """Create a DataFrame showing a valid Bearish Engulfing pattern."""
    # Uptrend
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
    full_prices = [100] * 20 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p + 1 for p in full_prices]
    
    # C1 (index -2): Open 120, Close 121 (Bullish)
    # C2 (index -1): Open 122, Close 118 (Bearish, Engulfs 120-121)
    opens[-2] = 120
    closes[-2] = 121
    opens[-1] = 122
    closes[-1] = 118
    highs[-1] = 123
    lows[-1] = 117
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Bearish Engulfing"

    def test_detect_returns_list(self, strategy, sample_bearish_engulfing_df):
        result = strategy.detect(sample_bearish_engulfing_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bearish_engulfing_detection(self, strategy, sample_bearish_engulfing_df):
        signals = strategy.detect(sample_bearish_engulfing_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH

    def test_no_uptrend_no_detection(self, strategy):
        # Flat/Downtrend
        prices = [120, 118, 116, 114, 112]
        full_prices = [120] * 30 + prices
        opens = [p + 1 for p in full_prices]
        closes = [p for p in full_prices]
        
        # C1 Bullish, C2 Engulfing, but in downtrend
        opens[-2] = 110
        closes[-2] = 111
        opens[-1] = 112
        closes[-1] = 108
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
