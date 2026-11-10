"""Tests for Standard Head and Shoulders"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.standard_head_and_shoulders import StandardHeadAndShoulders
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return StandardHeadAndShoulders()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_hs_breakdown_df():
    """Create a DataFrame showing a Standard Head and Shoulders with a breakdown."""
    size = 160
    full_prices = [140.0] * size
    full_prices[40] = 150.0 # LS
    full_prices[50] = 130.0 # T1
    full_prices[60] = 160.0 # Head
    full_prices[70] = 130.0 # T2
    full_prices[80] = 150.0 # RS
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # LS
    highs[40] = 150.0
    lows[40] = 149.0
    highs[39] = highs[41] = 145.0
    # T1
    lows[50] = 130.0
    highs[50] = 131.0
    lows[49] = lows[51] = 135.0
    # Head
    highs[60] = 160.0
    lows[60] = 159.0
    highs[59] = highs[61] = 155.0
    # T2
    lows[70] = 130.0
    highs[70] = 131.0
    lows[69] = lows[71] = 135.0
    # RS
    highs[80] = 150.0
    lows[80] = 149.0
    highs[79] = highs[81] = 145.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    closes[-1] = 125.0
    opens[-1] = 130.0
    highs[-1] = 130.5
    lows[-1] = 124.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Standard Head and Shoulders"

    def test_detect_returns_list(self, strategy, sample_hs_breakdown_df):
        result = strategy.detect(sample_hs_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_hs_breakdown(self, strategy, sample_hs_breakdown_df):
        signals = strategy.detect(sample_hs_breakdown_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_SELL for s in signals)
