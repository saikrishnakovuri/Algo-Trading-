"""Tests for Dark Cloud Cover"""
import pytest
import pandas as pd
from engine.candlestick_patterns.dark_cloud_cover import DarkCloudCover
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return DarkCloudCover()


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
def sample_dark_cloud_cover_df():
    """Create a DataFrame showing a valid Dark Cloud Cover pattern."""
    # Uptrend
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
    full_prices = [100] * 20 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p + 1 for p in full_prices]
    
    # C1 (index -2): Open 120, Close 130 (Strong Bullish)
    # C2 (index -1): Open 132 (Gap up), Close 124 (Midpoint of 120-130 is 125. 124 < 125).
    # 124 > 120 (Not engulfing)
    opens[-2] = 120
    closes[-2] = 130
    opens[-1] = 132
    closes[-1] = 124
    highs[-1] = 133
    lows[-1] = 123
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Dark Cloud Cover"

    def test_detect_returns_list(self, strategy, sample_dark_cloud_cover_df):
        result = strategy.detect(sample_dark_cloud_cover_df)
        assert isinstance(result, list)


class TestDetection:
    def test_dark_cloud_cover_detection(self, strategy, sample_dark_cloud_cover_df):
        signals = strategy.detect(sample_dark_cloud_cover_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH

    def test_no_gap_no_detection(self, strategy):
        # Uptrend
        prices = [100, 102, 104, 106, 108]
        full_prices = [100] * 20 + prices
        opens = [p for p in full_prices]
        closes = [p + 1 for p in full_prices]
        
        # C1 Bullish, C2 closes below midpoint but NO gap up
        opens[-2] = 110
        closes[-2] = 120
        opens[-1] = 120 # No gap up
        closes[-1] = 114
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_insufficient_penetration_no_detection(self, strategy):
        # Uptrend
        prices = [100, 102, 104, 106, 108]
        full_prices = [100] * 20 + prices
        opens = [p for p in full_prices]
        closes = [p + 1 for p in full_prices]
        
        # C1 Bullish, C2 gaps up but closes ABOVE midpoint
        opens[-2] = 110
        closes[-2] = 120 # Midpoint 115
        opens[-1] = 122
        closes[-1] = 117 # Closes above 115
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
