"""Tests for Head and Shoulders"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.head_and_shoulders import HeadAndShoulders
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return HeadAndShoulders()


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
    """Create a DataFrame showing a Head and Shoulders with a breakdown."""
    # 1. Left Shoulder at 150 (idx 40)
    # 2. Trough 1 at 130 (idx 50)
    # 3. Head at 160 (idx 60)
    # 4. Trough 2 at 130 (idx 70)
    # 5. Right Shoulder at 150 (idx 80)
    # 6. Breakdown at 125 (idx 149)
    
    size = 160
    # Background: 140
    full_prices = [140.0] * size
    
    # Manually set the key points
    # LS: idx 40, price 150
    full_prices[40] = 150.0
    # T1: idx 50, price 130
    full_prices[50] = 130.0
    # Head: idx 60, price 160
    full_prices[60] = 160.0
    # T2: idx 70, price 130
    full_prices[70] = 130.0
    # RS: idx 80, price 150
    full_prices[80] = 150.0
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure local extrema
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
    
    # Breakdown at end
    # Neckline is horizontal at 130. Close 125 is breakdown.
    closes[-1] = 125.0
    opens[-1] = 130.0
    highs[-1] = 130.5
    lows[-1] = 124.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Head and Shoulders"

    def test_detect_returns_list(self, strategy, sample_hs_breakdown_df):
        result = strategy.detect(sample_hs_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_hs_breakdown(self, strategy, sample_hs_breakdown_df):
        signals = strategy.detect(sample_hs_breakdown_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_SELL for s in signals)
