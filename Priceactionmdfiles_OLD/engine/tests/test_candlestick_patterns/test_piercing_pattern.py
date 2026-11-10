"""Tests for Piercing Pattern"""
import pytest
import pandas as pd
from engine.candlestick_patterns.piercing_pattern import PiercingPattern
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return PiercingPattern()


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
def sample_piercing_pattern_df():
    """Create a DataFrame showing a valid Piercing pattern."""
    # Downtrend
    prices = [120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
    full_prices = [120] * 20 + prices
    highs = [p + 1 for p in full_prices]
    lows = [p - 1 for p in full_prices]
    opens = [p + 1 for p in full_prices]
    closes = [p for p in full_prices]
    
    # C1 (index -2): Open 110, Close 100 (Strong Bearish)
    # C2 (index -1): Open 98 (Gap down), Close 106 (Midpoint of 100-110 is 105. 106 > 105).
    # 106 < 110 (Not engulfing)
    opens[-2] = 110
    closes[-2] = 100
    opens[-1] = 98
    closes[-1] = 106
    highs[-1] = 107
    lows[-1] = 97
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Piercing Pattern"

    def test_detect_returns_list(self, strategy, sample_piercing_pattern_df):
        result = strategy.detect(sample_piercing_pattern_df)
        assert isinstance(result, list)


class TestDetection:
    def test_piercing_pattern_detection(self, strategy, sample_piercing_pattern_df):
        signals = strategy.detect(sample_piercing_pattern_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].market_bias == MarketBias.BULLISH

    def test_no_gap_no_detection(self, strategy):
        # Downtrend
        prices = [120, 118, 116, 114, 112, 110]
        full_prices = [120] * 20 + prices
        opens = [p + 1 for p in full_prices]
        closes = [p for p in full_prices]
        
        # C1 Bearish, C2 closes above midpoint but NO gap down
        opens[-2] = 110
        closes[-2] = 100
        opens[-1] = 100 # No gap down
        closes[-1] = 106
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0

    def test_insufficient_penetration_no_detection(self, strategy):
        # Downtrend
        prices = [120, 118, 116, 114, 112, 110]
        full_prices = [120] * 20 + prices
        opens = [p + 1 for p in full_prices]
        closes = [p for p in full_prices]
        
        # C1 Bearish, C2 gaps down but closes BELOW midpoint
        opens[-2] = 110
        closes[-2] = 100 # Midpoint 105
        opens[-1] = 98
        closes[-1] = 103 # Closes below 105
        
        df = create_ohlcv(opens, [p+1 for p in opens], [p-1 for p in opens], closes)
        signals = strategy.detect(df)
        assert len(signals) == 0
