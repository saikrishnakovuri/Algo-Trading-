"""Tests for Breakout Trap"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.breakout_trap import BreakoutTrap
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BreakoutTrap()


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
def sample_bearish_trap_df():
    """Create a DataFrame showing a Bearish Breakout Trap (Fakeout of Resistance)."""
    size = 150
    # 1. Level at 150 (Resistance)
    full_prices = [140.0] * size
    
    # 2. Establish Resistance in the levels detection window (idx 70 to 140)
    for i in [80, 90, 100]:
        full_prices[i] = 150.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p for p in full_prices]
    
    # Establish peaks at 150
    for idx in [80, 90, 100]:
        highs[idx] = 150.0
        lows[idx] = 148.0
        highs[idx-1] = highs[idx+1] = 145.0
        
    # Breakout candle (idx 148)
    opens[148] = 145.0
    closes[148] = 155.0
    highs[148] = 156.0
    
    # Trap candle (idx 149)
    opens[149] = 155.0
    closes[149] = 148.0
    highs[149] = 157.0 # Swept liquidity
    
    volumes = [1000] * size
    volumes[149] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Breakout Trap"

    def test_detect_returns_list(self, strategy, sample_bearish_trap_df):
        result = strategy.detect(sample_bearish_trap_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bearish_trap(self, strategy, sample_bearish_trap_df):
        signals = strategy.detect(sample_bearish_trap_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
