"""Tests for Inverse Head and Shoulders"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.inverse_head_and_shoulders import InverseHeadAndShoulders
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return InverseHeadAndShoulders()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_ihs_breakout_df():
    """Create a DataFrame showing an Inverse Head and Shoulders with a breakout."""
    # 1. Left Shoulder at 100 (idx 40)
    # 2. Peak 1 at 120 (idx 50)
    # 3. Head at 90 (idx 60)
    # 4. Peak 2 at 120 (idx 70)
    # 5. Right Shoulder at 100 (idx 80)
    # 6. Breakout at 125 (idx 149)
    
    size = 160
    # Background: 110
    full_prices = [110.0] * size
    
    # LS: idx 40, price 100
    full_prices[40] = 100.0
    # P1: idx 50, price 120
    full_prices[50] = 120.0
    # Head: idx 60, price 90
    full_prices[60] = 90.0
    # P2: idx 70, price 120
    full_prices[70] = 120.0
    # RS: idx 80, price 100
    full_prices[80] = 100.0
    
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    
    # Ensure local extrema
    # LS
    lows[40] = 100.0
    highs[40] = 101.0
    lows[39] = lows[41] = 105.0
    
    # P1
    highs[50] = 120.0
    lows[50] = 119.0
    highs[49] = highs[51] = 115.0
    
    # Head
    lows[60] = 90.0
    highs[60] = 91.0
    lows[59] = lows[61] = 95.0
    
    # P2
    highs[70] = 120.0
    lows[70] = 119.0
    highs[69] = highs[71] = 115.0
    
    # RS
    lows[80] = 100.0
    highs[80] = 101.0
    lows[79] = lows[81] = 105.0
    
    opens = [(h+l)/2 for h, l in zip(highs, lows)]
    closes = [o + 0.1 for o in opens]
    
    # Breakout at end
    # Neckline is horizontal at 120. Close 125 is breakout.
    closes[-1] = 125.0
    opens[-1] = 120.0
    highs[-1] = 125.5
    lows[-1] = 119.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Inverse Head and Shoulders"

    def test_detect_returns_list(self, strategy, sample_ihs_breakout_df):
        result = strategy.detect(sample_ihs_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_ihs_breakout(self, strategy, sample_ihs_breakout_df):
        signals = strategy.detect(sample_ihs_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.STRONG_BUY for s in signals)
