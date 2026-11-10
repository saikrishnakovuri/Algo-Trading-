"""Tests for Supply & Demand"""
import pytest
import pandas as pd
from engine.advanced_concepts.supply_demand import SupplyDemand
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return SupplyDemand()


def create_ohlcv(opens, highs, lows, closes):
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': [1000] * len(opens)
    })


@pytest.fixture
def sample_demand_retest_df():
    """Create a DataFrame showing a Demand Zone followed by retest."""
    # Increasing lead-in to 80 + 30 + 11 = 121 candles
    full_prices = [100] * 80 + [110] * 30 + [120, 115, 110, 108, 107, 125, 128, 122, 115, 110, 108]
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    
    # Departure candle index 115: Open 107, Close 125
    # (80+30+5 = 115)
    opens[115] = 107
    highs[115] = 125.5
    lows[115] = 106.5
    
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_supply_retest_df():
    """Create a DataFrame showing a Supply Zone followed by retest."""
    # Increasing lead-in to 121 candles
    full_prices = [100] * 80 + [90] * 30 + [80, 85, 90, 92, 93, 75, 72, 80, 88, 92, 93]
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    
    # Departure candle index 115: Open 93, Close 75
    opens[115] = 93
    highs[115] = 93.5
    lows[115] = 74.5
    
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Supply & Demand"

    def test_detect_returns_list(self, strategy, sample_demand_retest_df):
        result = strategy.detect(sample_demand_retest_df)
        assert isinstance(result, list)


class TestDetection:
    def test_demand_retest(self, strategy, sample_demand_retest_df):
        signals = strategy.detect(sample_demand_retest_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)

    def test_supply_retest(self, strategy, sample_supply_retest_df):
        signals = strategy.detect(sample_supply_retest_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
