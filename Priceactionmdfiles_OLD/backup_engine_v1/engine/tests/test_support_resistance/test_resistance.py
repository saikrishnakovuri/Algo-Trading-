"""Tests for Resistance"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.resistance import Resistance
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return Resistance()


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
def sample_resistance_rejection_df():
    """Create a DataFrame showing a clean Resistance Rejection."""
    size = 150
    # 1. Background prices
    full_prices = [100.0] * size
    
    # 2. Establish Resistance at 120 (idx 40, 60, 80)
    for idx in [40, 60, 80]:
        full_prices[idx] = 120.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure peaks are local extrema
    for idx in [40, 60, 80]:
        highs[idx] = 120.0
        lows[idx] = 118.0
        highs[idx-1] = highs[idx+1] = 115.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Final candle (idx 149): Rejection at resistance
    highs[149] = 120.1 # Touches 120
    opens[149] = 118.0
    closes[149] = 117.0 # Bearish close
    lows[149] = 116.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Resistance"

    def test_detect_returns_list(self, strategy, sample_resistance_rejection_df):
        result = strategy.detect(sample_resistance_rejection_df)
        assert isinstance(result, list)


class TestDetection:
    def test_resistance_rejection(self, strategy, sample_resistance_rejection_df):
        signals = strategy.detect(sample_resistance_rejection_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
