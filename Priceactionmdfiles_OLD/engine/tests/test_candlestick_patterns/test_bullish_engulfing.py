"""Tests for Bullish Engulfing"""
import pytest
import pandas as pd
from engine.candlestick_patterns.bullish_engulfing import BullishEngulfing
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BullishEngulfing()


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
def sample_bullish_engulfing_df():
    """Create a DataFrame showing a valid Bullish Engulfing pattern."""
    # Downtrend
    prices = [120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
    full_prices = [120] * 20 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p + 1 for p in full_prices]
    closes = [p for p in full_prices]
    
    # C1 (index -2): Open 101, Close 100 (Bearish)
    # C2 (index -1): Open 99, Close 103 (Bullish, Engulfs 100-101)
    opens[-2] = 101
    closes[-2] = 100
    opens[-1] = 99
    closes[-1] = 103
    highs[-1] = 104
    lows[-1] = 98
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Bullish Engulfing"

    def test_detect_returns_list(self, strategy, sample_bullish_engulfing_df):
        result = strategy.detect(sample_bullish_engulfing_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_engulfing_detection(self, strategy, sample_bullish_engulfing_df):
        signals = strategy.detect(sample_bullish_engulfing_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].market_bias == MarketBias.BULLISH

    def test_no_downtrend_no_detection(self, strategy):
        # Flat/Uptrend
        prices = [100, 102, 104, 106, 108]
        full_prices = [100] * 30 + prices
        opens = [p for p in full_prices]
        closes = [p + 1 for p in full_prices]
        
        # C1 Bearish, C2 Engulfing, but in uptrend
        opens[-2] = 110
        closes[-2] = 109
        opens[-1] = 108
        closes[-1] = 112
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
