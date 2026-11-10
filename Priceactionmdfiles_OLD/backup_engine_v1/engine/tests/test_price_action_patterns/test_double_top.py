"""Tests for Double Top"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.double_top import DoubleTop
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return DoubleTop()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_double_top_breakdown_df():
    """Create a DataFrame showing a Double Top with a breakdown."""
    # 1. First Top at 150 (idx 40)
    # 2. Neckline at 130 (idx 60)
    # 3. Second Top at 150 (idx 80)
    # 4. Breakdown at 125 (idx 149)
    
    size = 150
    # Background: 140.0
    full_prices = [140.0] * size
    
    # T1: idx 40, price 150
    full_prices[40] = 150.0
    # Neckline: idx 60, price 130
    full_prices[60] = 130.0
    # T2: idx 80, price 150
    full_prices[80] = 150.0
    
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    
    # Ensure peaks/troughs are local extrema
    # T1
    highs[40] = 150.0
    lows[40] = 149.0
    highs[39] = highs[41] = 148.0
    
    # Neckline
    lows[60] = 130.0
    highs[60] = 131.0
    lows[59] = lows[61] = 132.0
    
    # T2
    highs[80] = 150.0
    lows[80] = 149.0
    highs[79] = highs[81] = 148.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o - 0.1 for o in opens]
    
    # Breakdown at end
    closes[-1] = 125.0
    opens[-1] = 130.0
    highs[-1] = 130.5
    lows[-1] = 124.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Double Top"

    def test_detect_returns_list(self, strategy, sample_double_top_breakdown_df):
        result = strategy.detect(sample_double_top_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_double_top_breakdown(self, strategy, sample_double_top_breakdown_df):
        signals = strategy.detect(sample_double_top_breakdown_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_SELL for s in signals)
