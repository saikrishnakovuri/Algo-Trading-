"""Tests for Triple Top"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.triple_top import TripleTop
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return TripleTop()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_triple_top_breakdown_df():
    """Create a DataFrame showing a Triple Top with a breakdown."""
    # 1. T1 at 150 (idx 40)
    # 2. B1 at 130 (idx 50)
    # 3. T2 at 150 (idx 60)
    # 4. B2 at 130 (idx 70)
    # 5. T3 at 150 (idx 80)
    # 6. Breakdown at 125 (idx 149)
    
    size = 160
    # Background: 140
    full_prices = [140.0] * size
    
    # Manually set the key points
    full_prices[40] = 150.0 # T1
    full_prices[50] = 130.0 # B1
    full_prices[60] = 150.0 # T2
    full_prices[70] = 130.0 # B2
    full_prices[80] = 150.0 # T3
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure local extrema
    for idx in [40, 60, 80]: # Tops
        highs[idx] = 150.0
        lows[idx] = 149.0
        highs[idx-1] = highs[idx+1] = 145.0
        
    for idx in [50, 70]: # Bottoms
        lows[idx] = 130.0
        highs[idx] = 131.0
        lows[idx-1] = lows[idx+1] = 135.0
        
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o - 0.1 for o in opens]
    
    # Final breakdown candle
    closes[-1] = 125.0
    opens[-1] = 130.0
    highs[-1] = 130.5
    lows[-1] = 124.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Triple Top"

    def test_detect_returns_list(self, strategy, sample_triple_top_breakdown_df):
        result = strategy.detect(sample_triple_top_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_triple_top_breakdown(self, strategy, sample_triple_top_breakdown_df):
        signals = strategy.detect(sample_triple_top_breakdown_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_SELL for s in signals)
