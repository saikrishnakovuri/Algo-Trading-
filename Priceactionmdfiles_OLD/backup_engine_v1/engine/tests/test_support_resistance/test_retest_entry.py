"""Tests for Retest Entry"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.retest_entry import RetestEntry
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return RetestEntry()


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
def sample_bullish_retest_df():
    """Create a DataFrame showing a Bullish Retest setup."""
    size = 150
    # 1. Level at 120 (Resistance)
    full_prices = [110.0] * size
    for i in [45, 55]:
        full_prices[i] = 120.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p for p in full_prices]
    
    # Establish Resistance
    for idx in [45, 55]:
        highs[idx] = 120.0
        lows[idx] = 118.0
        highs[idx-1] = highs[idx+1] = 115.0
        
    # 2. Breakout candle (idx 130)
    opens[130] = 119.0
    closes[130] = 125.0
    highs[130] = 126.0
    
    # 3. Retest candle at end (idx 149)
    # Price returns to 120.5 and rejects
    opens[149] = 122.0
    closes[149] = 123.0
    lows[149] = 120.2 # Retest
    highs[149] = 123.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Retest Entry"

    def test_detect_returns_list(self, strategy, sample_bullish_retest_df):
        result = strategy.detect(sample_bullish_retest_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_retest(self, strategy, sample_bullish_retest_df):
        signals = strategy.detect(sample_bullish_retest_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
