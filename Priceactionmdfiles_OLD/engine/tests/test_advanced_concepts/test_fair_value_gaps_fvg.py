"""Tests for Fair Value Gaps (FVG)"""
import pytest
import pandas as pd
from engine.advanced_concepts.fair_value_gaps_fvg import FairValueGaps
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return FairValueGaps()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_bullish_fvg_mitigation_df():
    """Create a DataFrame showing a Bullish FVG followed by mitigation."""
    # Prices: ..., 105 (C1), 115 (C2), 112 (C3), ..., 107 (Mitigation)
    prices = [100, 102, 105, 115, 112, 110, 108, 107]
    full_prices = [100] * 50 + prices
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    
    # C1 (index 52): High 105.1
    # C2 (index 53): Open 105, Close 115 (Displacement)
    # C3 (index 54): Low 112 - 0.1 = 111.9
    # Gap: 105.1 to 111.9
    opens[53] = 105
    highs[53] = 115.5
    lows[53] = 104.5
    
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_bearish_fvg_mitigation_df():
    """Create a DataFrame showing a Bearish FVG followed by mitigation."""
    # Prices: ..., 95 (C1), 85 (C2), 88 (C3), ..., 92 (Mitigation)
    prices = [100, 98, 95, 85, 88, 90, 91, 92]
    full_prices = [100] * 50 + prices
    highs = [p + 0.1 for p in full_prices]
    lows = [p - 0.1 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    
    # C1 (index 52): Low 94.9
    # C2 (index 53): Open 95, Close 85 (Displacement)
    # C3 (index 54): High 88.1
    # Gap: 88.1 to 94.9
    opens[53] = 95
    highs[53] = 95.5
    lows[53] = 84.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Fair Value Gaps (FVG)"

    def test_detect_returns_list(self, strategy, sample_bullish_fvg_mitigation_df):
        result = strategy.detect(sample_bullish_fvg_mitigation_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_fvg_mitigation(self, strategy, sample_bullish_fvg_mitigation_df):
        signals = strategy.detect(sample_bullish_fvg_mitigation_df)
        assert len(signals) > 0
        # Should detect BUY signal since price (107) is in gap (105.1-110.1)
        assert any(s.signal_type == SignalType.BUY for s in signals)

    def test_bearish_fvg_mitigation(self, strategy, sample_bearish_fvg_mitigation_df):
        signals = strategy.detect(sample_bearish_fvg_mitigation_df)
        assert len(signals) > 0
        # Should detect SELL signal since price (92) is in gap (89.9-94.9)
        assert any(s.signal_type == SignalType.SELL for s in signals)
