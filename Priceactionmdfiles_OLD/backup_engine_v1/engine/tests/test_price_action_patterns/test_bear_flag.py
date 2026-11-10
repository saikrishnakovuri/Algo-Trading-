"""Tests for Bear Flag"""
import pytest
import pandas as pd
import numpy as np
from engine.price_action_patterns.bear_flag import BearFlag
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return BearFlag()


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
def sample_bear_flag_breakdown_df():
    """Create a DataFrame showing a Bear Flag with a breakdown at the end."""
    # 1. Initialize arrays
    size = 150
    full_prices = [100.0] * size
    
    # 2. Flagpole (Drop from 100 to 80 over 10 candles)
    # Move to indices 120 to 130
    for i, val in enumerate(np.linspace(100, 80, 11)):
        full_prices[120 + i] = val
        
    # 3. Flag (Consolidation from 80 to 85 over 15 candles)
    # indices 130 to 145
    for i, val in enumerate(np.linspace(80, 85, 16)):
        full_prices[130 + i] = val
        
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p + 0.1 for p in full_prices]
    closes = [p for p in full_prices]
    
    # Adjust flag lows to be a rising trendline (indices 130 to 148)
    for i in range(130, 149):
        lows[i] = 80 + (i-130)*0.3 # 80 to 85.4
        highs[i] = lows[i] + 2.0
        opens[i] = highs[i] - 0.5
        closes[i] = lows[i] + 0.5
        
    # 4. Final candle (index 149): Breakdown (Drop to 75)
    closes[149] = 75.0
    opens[149] = 85.0
    highs[149] = 85.5
    lows[149] = 74.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Bear Flag"

    def test_detect_returns_list(self, strategy, sample_bear_flag_breakdown_df):
        result = strategy.detect(sample_bear_flag_breakdown_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bear_flag_breakdown(self, strategy, sample_bear_flag_breakdown_df):
        signals = strategy.detect(sample_bear_flag_breakdown_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
