"""Tests for Double Bottom"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.double_bottom import DoubleBottom
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return DoubleBottom()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_double_bottom_breakout_df():
    """Create a DataFrame showing a Double Bottom with a breakout."""
    # 1. First Bottom at 100 (idx 40)
    # 2. Neckline at 120 (idx 60)
    # 3. Second Bottom at 100 (idx 80)
    # 4. Breakout at 125 (idx 149)
    
    size = 150
    # Background: 110.0 (between 100 and 120)
    full_prices = [110.0] * size
    
    # B1: idx 40, price 100
    full_prices[40] = 100.0
    # Neckline: idx 60, price 120
    full_prices[60] = 120.0
    # B2: idx 80, price 100
    full_prices[80] = 100.0
    
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    
    # Ensure peaks/troughs are local extrema
    # B1
    lows[40] = 100.0
    highs[40] = 101.0
    lows[39] = lows[41] = 102.0
    
    # Neckline
    highs[60] = 120.0
    lows[60] = 119.0
    highs[59] = highs[61] = 118.0
    
    # B2
    lows[80] = 100.0
    highs[80] = 101.0
    lows[79] = lows[81] = 102.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Breakout at end
    closes[-1] = 125.0
    opens[-1] = 120.0
    highs[-1] = 125.5
    lows[-1] = 119.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Double Bottom"

    def test_detect_returns_list(self, strategy, sample_double_bottom_breakout_df):
        result = strategy.detect(sample_double_bottom_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_double_bottom_breakout(self, strategy, sample_double_bottom_breakout_df):
        signals = strategy.detect(sample_double_bottom_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
