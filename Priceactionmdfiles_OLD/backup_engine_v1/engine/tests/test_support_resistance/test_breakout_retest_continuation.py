"""Tests for Breakout -> Retest -> Continuation"""
import pytest
import pandas as pd
import numpy as np
from engine.support_resistance.breakout_retest_continuation import BreakoutRetestContinuation
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BreakoutRetestContinuation()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_bullish_brc_df():
    """Create a DataFrame showing a Bullish B-R-C setup."""
    size = 150
    # 1. Level at 120 (Resistance)
    full_prices = [110.0] * size
    
    # 2. Establish Resistance in the older data (idx 40 to 60)
    for i in [45, 55]:
        full_prices[i] = 120.0
        
    # 3. Breakout (idx 130)
    full_prices[130] = 125.0
    
    # 4. Retest (idx 140)
    full_prices[140] = 120.5
    
    # 5. Continuation (idx 149)
    full_prices[149] = 128.0
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = [p for p in full_prices]
    
    # LS Resistance Peak
    highs[45] = 120.0
    lows[45] = 119.0
    highs[55] = 120.0
    lows[55] = 119.0
    
    # Breakout candle
    opens[130] = 119.0
    closes = [p for p in full_prices]
    closes[130] = 125.0
    highs[130] = 125.5
    
    # Retest candle
    lows[140] = 120.2 # Touches 120
    closes[140] = 121.0
    
    # Continuation candle
    closes[149] = 128.0
    opens[149] = 124.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Breakout-Retest-Continuation"

    def test_detect_returns_list(self, strategy, sample_bullish_brc_df):
        result = strategy.detect(sample_bullish_brc_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_brc(self, strategy, sample_bullish_brc_df):
        signals = strategy.detect(sample_bullish_brc_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
