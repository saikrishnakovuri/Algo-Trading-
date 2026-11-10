"""Tests for Triple Bottom"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.triple_bottom import TripleBottom
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return TripleBottom()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_triple_bottom_breakout_df():
    """Create a DataFrame showing a Triple Bottom with a breakout."""
    # 1. B1 at 100 (idx 40)
    # 2. P1 at 120 (idx 50)
    # 3. B2 at 100 (idx 60)
    # 4. P2 at 120 (idx 70)
    # 5. B3 at 100 (idx 80)
    # 6. Breakout at 125 (idx 149)
    
    size = 160
    # Background: 110
    full_prices = [110.0] * size
    
    # Manually set the key points
    full_prices[40] = 100.0 # B1
    full_prices[50] = 120.0 # P1
    full_prices[60] = 100.0 # B2
    full_prices[70] = 120.0 # P2
    full_prices[80] = 100.0 # B3
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure local extrema
    for idx in [40, 60, 80]: # Bottoms
        lows[idx] = 100.0
        highs[idx] = 101.0
        lows[idx-1] = lows[idx+1] = 105.0
        
    for idx in [50, 70]: # Peaks
        highs[idx] = 120.0
        lows[idx] = 119.0
        highs[idx-1] = highs[idx+1] = 115.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Final breakout candle
    closes[-1] = 125.0
    opens[-1] = 120.0
    highs[-1] = 125.5
    lows[-1] = 119.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Triple Bottom"

    def test_detect_returns_list(self, strategy, sample_triple_bottom_breakout_df):
        result = strategy.detect(sample_triple_bottom_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_triple_bottom_breakout(self, strategy, sample_triple_bottom_breakout_df):
        signals = strategy.detect(sample_triple_bottom_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
