"""Tests for Liquidity Grab"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.liquidity_grab import LiquidityGrab
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return LiquidityGrab()


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
def sample_bullish_grab_df():
    """Create a DataFrame showing a Bullish Liquidity Grab (Support Sweep)."""
    size = 150
    # 1. Level at 100 (Support)
    full_prices = [110.0] * size
    for i in [80, 90, 100]:
        full_prices[i] = 100.0
        
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p for p in full_prices]
    
    # Establish troughs at 100
    for idx in [80, 90, 100]:
        lows[idx] = 100.0
        highs[idx] = 102.0
        lows[idx-1] = lows[idx+1] = 105.0
        
    # Grab candle at end (idx 149)
    # Price sweeps to 95 and rejects to close at 103.
    lows[149] = 95.0
    opens[149] = 102.0
    closes[149] = 103.0
    highs[149] = 103.5
    
    # Range 103.5 - 95.0 = 8.5
    # Lower wick 102 - 95 = 7.0. 7.0 > 8.5 * 0.4 = 3.4. Correct.
    
    volumes = [1000] * size
    volumes[149] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Liquidity Grab"

    def test_detect_returns_list(self, strategy, sample_bullish_grab_df):
        result = strategy.detect(sample_bullish_grab_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_grab(self, strategy, sample_bullish_grab_df):
        signals = strategy.detect(sample_bullish_grab_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
