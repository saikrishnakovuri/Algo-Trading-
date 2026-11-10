"""Tests for Support Breakdown"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.support_breakdown import SupportBreakdown
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return SupportBreakdown()


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
def sample_sup_breakdown_df():
    """Create a DataFrame showing a clean Support Breakdown."""
    size = 150
    # 1. Falling trend with RSI < 40
    full_prices = [150.0 - i*0.1 for i in range(size)]
    
    # 2. Establish Support in window
    for i in [80, 90, 100]:
        full_prices[i] = 120.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p for p in full_prices]
    
    # Troughs at 120
    for idx in [80, 90, 100]:
        lows[idx] = 120.0
        highs[idx] = 122.0
        lows[idx-1] = lows[idx+1] = 125.0
        
    # Breakdown candle (idx 149)
    opens[149] = 122.0
    closes[149] = 115.0
    lows[149] = 114.0
    
    volumes = [1000] * size
    volumes[149] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Support Breakdown"

    def test_detect_returns_list(self, strategy, sample_sup_breakdown_df):
        result = strategy.detect(sample_sup_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_sup_breakdown(self, strategy, sample_sup_breakdown_df):
        signals = strategy.detect(sample_sup_breakdown_df)
        assert len(signals) > 0
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].market_bias == MarketBias.BEARISH
