"""Tests for Support"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.support import Support
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return Support()


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
def sample_support_rejection_df():
    """Create a DataFrame showing a clean Support Rejection."""
    size = 150
    # 1. Background prices
    full_prices = [120.0] * size
    
    # 2. Establish Support at 100 (idx 40, 60, 80)
    for idx in [40, 60, 80]:
        full_prices[idx] = 100.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure troughs are local extrema
    for idx in [40, 60, 80]:
        lows[idx] = 100.0
        highs[idx] = 102.0
        lows[idx-1] = lows[idx+1] = 105.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Final candle (idx 149): Rejection at support
    lows[149] = 99.9 # Touches 100
    opens[149] = 102.0
    closes[149] = 103.0 # Bullish close
    highs[149] = 103.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Support"

    def test_detect_returns_list(self, strategy, sample_support_rejection_df):
        result = strategy.detect(sample_support_rejection_df)
        assert isinstance(result, list)


class TestDetection:
    def test_support_rejection(self, strategy, sample_support_rejection_df):
        signals = strategy.detect(sample_support_rejection_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
