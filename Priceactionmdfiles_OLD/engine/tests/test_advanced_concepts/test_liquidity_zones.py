"""Tests for Liquidity Zones"""
import pytest
import pandas as pd
from engine.advanced_concepts.liquidity_zones import LiquidityZones
from engine.signal import Signal, SignalType, MarketBias


@pytest.fixture
def strategy():
    return LiquidityZones()


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
def sample_bullish_sweep_df():
    """Create a DataFrame showing a Sell-Side Liquidity Sweep."""
    # 1. Significant Low at index 80 (price 100)
    # 2. Current candle sweeps below 100 and rejects
    prices = [110] * 80 + [105, 102, 100, 103, 105, 107, 104, 102, 103]
    # index 82: 100 (Swing Low)
    # index 88: Sweep candle. low=98, close=103.
    
    full_prices = [120] * 50 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    volumes = [1000] * len(full_prices)
    
    # Sweep candle index 138 (50+88): Low 98, Close 103
    lows[138] = 98
    opens[138] = 101
    closes[138] = 103
    volumes[138] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


@pytest.fixture
def sample_bearish_sweep_df():
    """Create a DataFrame showing a Buy-Side Liquidity Sweep."""
    # 1. Significant High at index 80 (price 150)
    # 2. Current candle sweeps above 150 and rejects
    prices = [140] * 80 + [145, 148, 150, 147, 145, 142, 146, 148, 147]
    full_prices = [130] * 50 + prices
    highs = [p + 0.5 for p in full_prices]
    lows = [p - 0.5 for p in full_prices]
    opens = [p for p in full_prices]
    closes = full_prices
    volumes = [1000] * len(full_prices)
    
    # Sweep candle index 138: High 152, Close 147
    highs[138] = 152
    opens[138] = 149
    closes[138] = 147
    volumes[138] = 3000
    
    return create_ohlcv(opens, highs, lows, closes, volumes)


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name == "Liquidity Zones"

    def test_detect_returns_list(self, strategy, sample_bullish_sweep_df):
        result = strategy.detect(sample_bullish_sweep_df)
        assert isinstance(result, list)


class TestDetection:
    def test_bullish_sweep(self, strategy, sample_bullish_sweep_df):
        signals = strategy.detect(sample_bullish_sweep_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.BUY for s in signals)
        assert any(s.market_bias == MarketBias.BULLISH for s in signals)

    def test_bearish_sweep(self, strategy, sample_bearish_sweep_df):
        signals = strategy.detect(sample_bearish_sweep_df)
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.SELL for s in signals)
        assert any(s.market_bias == MarketBias.BEARISH for s in signals)
