"""Tests for Horizontal Channel"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.horizontal_channel import HorizontalChannel
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return HorizontalChannel()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_horizontal_channel_df():
    """Create a DataFrame showing a clean Horizontal Channel."""
    size = 150
    # Range: Support 100, Resistance 120
    # Oscillation between 100 and 120
    idx = np.arange(size)
    osc = 10 * np.sin(idx/5) + 110 # Oscillates between 100 and 120
    
    highs = osc + 1.0
    lows = osc - 1.0
    
    # We need to manually set some points to hit boundaries exactly for the count
    # Support (100): 
    for i in [115, 125, 135]:
        lows[i] = 100.0
        highs[i] = 105.0
    # Resistance (120):
    for i in [110, 120, 130, 140]:
        highs[i] = 120.0
        lows[i] = 115.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Final price near support
    closes[-1] = 102.0
    opens[-1] = 103.0
    highs[-1] = 104.0
    lows[-1] = 100.0
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Horizontal Channel"

    def test_detect_returns_list(self, strategy, sample_horizontal_channel_df):
        result = strategy.detect(sample_horizontal_channel_df)
        assert isinstance(result, list)


class TestDetection:
    def test_horizontal_channel_support_buy(self, strategy, sample_horizontal_channel_df):
        signals = strategy.detect(sample_horizontal_channel_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
