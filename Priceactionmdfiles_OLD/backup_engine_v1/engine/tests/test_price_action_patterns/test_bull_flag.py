"""Tests for Bull Flag"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.bull_flag import BullFlag
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BullFlag()


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
def sample_bull_flag_breakout_df():
    """Create a DataFrame showing a Bull Flag with a breakout at the end."""
    # 1. Initialize arrays
    size = 150
    full_prices = [100.0] * size
    
    # 2. Flagpole (Rise from 100 to 120 over 10 candles)
    # Move to indices 120 to 130
    for i, val in enumerate(np.linspace(100, 120, 11)):
        full_prices[120 + i] = val
        
    # 3. Flag (Consolidation from 120 to 115 over 15 candles)
    # indices 130 to 145
    for i, val in enumerate(np.linspace(120, 115, 16)):
        full_prices[130 + i] = val
        
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p - 0.1 for p in full_prices]
    closes = [p for p in full_prices]
    
    # Adjust flag highs to be a descending trendline (indices 130 to 148)
    for i in range(130, 149):
        highs[i] = 120 - (i-130)*0.3 # 120 to 114.6
        lows[i] = highs[i] - 2.0
        opens[i] = lows[i] + 0.5
        closes[i] = highs[i] - 0.5
        
    # 4. Final candle (index 149): Breakout (Rise to 125)
    closes[149] = 125.0
    opens[149] = 115.0
    highs[149] = 125.5
    lows[149] = 114.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Bull Flag"

    def test_detect_returns_list(self, strategy, sample_bull_flag_breakout_df):
        result = strategy.detect(sample_bull_flag_breakout_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bull_flag_breakout(self, strategy, sample_bull_flag_breakout_df):
        signals = strategy.detect(sample_bull_flag_breakout_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)
