"""Tests for Order Blocks"""
import pytest
import pandas as pd
from engine.advanced_concepts.order_blocks import OrderBlocks
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return OrderBlocks()


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
def sample_bullish_ob_mitigation_df():
    """Create a DataFrame showing a Bullish OB followed by mitigation."""
    # Prices: ..., 110 (SH), 105, 102 (OB), 115 (BOS), 102 (Mitigation)
    prices = [100, 105, 110, 108, 105, 102, 115, 118, 112, 108, 104, 102]
    full_prices = [100] * 90 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    opens[95] = 103 # OB Bearish candle
    closes = full_prices
    opens[96] = 103 # Displacement
    return create_ohlcv(opens, highs, lows, closes)


@pytest.fixture
def sample_bearish_ob_mitigation_df():
    """Create a DataFrame showing a Bearish OB followed by mitigation."""
    # Prices: ..., 90 (SL), 95, 98 (OB), 85 (BOS), 98 (Mitigation)
    prices = [100, 95, 90, 92, 95, 98, 85, 82, 88, 92, 96, 98]
    full_prices = [100] * 90 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    opens[95] = 97 # OB Bullish candle
    closes = full_prices
    opens[96] = 97 # Displacement
    return create_ohlcv(opens, highs, lows, closes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Order Blocks"

    def test_detect_returns_list(self, strategy, sample_bullish_ob_mitigation_df):
        result = strategy.detect(sample_bullish_ob_mitigation_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_ob_mitigation(self, strategy, sample_bullish_ob_mitigation_df):
        signals = strategy.detect(sample_bullish_ob_mitigation_df)
        assert len(signals) > 0
        # Should detect a BUY signal at mitigation
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)

    def test_bearish_ob_mitigation(self, strategy, sample_bearish_ob_mitigation_df):
        signals = strategy.detect(sample_bearish_ob_mitigation_df)
        assert len(signals) > 0
        # Should detect a SELL signal at mitigation
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
