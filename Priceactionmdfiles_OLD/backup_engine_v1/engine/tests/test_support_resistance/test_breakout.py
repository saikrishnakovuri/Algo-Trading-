"""Tests for Breakout"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.breakout import Breakout
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return Breakout()


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
def sample_bullish_breakout_df():
    """Create a DataFrame showing a Bullish Breakout."""
    size = 150
    # 1. Resistance at 150
    full_prices = [140.0] * size
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
        
    # Breakout candle (idx 149)
    opens[149] = 145.0
    closes[149] = 155.0
    highs[149] = 156.0
    
    volumes = [1000] * size
    volumes[149] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Breakout"

    def test_detect_returns_list(self, strategy, sample_bullish_breakout_df):
        result = strategy.detect(sample_bullish_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_breakout(self, strategy, sample_bullish_breakout_df):
        signals = strategy.detect(sample_bullish_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
