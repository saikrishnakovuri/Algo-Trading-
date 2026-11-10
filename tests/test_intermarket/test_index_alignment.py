import pytest
import pandas as pd
import numpy as np
from modules.intermarket.index_alignment import IndexAlignmentChecker
from modules.intermarket.schemas import IndexContext

def create_mock_ohlcv(price_trend: str, length: int = 100):
    """
    price_trend: 'bullish', 'bearish', 'neutral'
    """
    base = 22000.0
    if price_trend == 'bullish':
        data = base + np.linspace(0, 100, length)
    elif price_trend == 'bearish':
        data = base - np.linspace(0, 100, length)
    else:
        data = np.full(length, base)
        
    df = pd.DataFrame({
        'Open': data, 'High': data + 5, 'Low': data - 5, 'Close': data, 'Volume': np.random.randint(1000, 5000, length)
    })
    return df

def test_index_alignment_bullish():
    checker = IndexAlignmentChecker()
    ohlcv_5m = create_mock_ohlcv('bullish', 100)
    ohlcv_15m = create_mock_ohlcv('bullish', 50)
    
    ctx = IndexContext("NIFTY", ohlcv_5m, ohlcv_15m, 22000.0, "TRENDING")
    
    verdict = checker.evaluate("RELIANCE", "LONG", ctx)
    assert verdict.nifty_state == "STRONG_BULL"
    assert verdict.alignment == "ALIGNED_STRONG"
    assert verdict.score_delta == 1.0
    assert not verdict.veto

def test_index_alignment_veto():
    checker = IndexAlignmentChecker()
    ohlcv_5m = create_mock_ohlcv('bearish', 100)
    ohlcv_15m = create_mock_ohlcv('bearish', 50)
    
    ctx = IndexContext("NIFTY", ohlcv_5m, ohlcv_15m, 22100.0, "TRENDING")
    
    verdict = checker.evaluate("RELIANCE", "LONG", ctx)
    assert verdict.nifty_state == "STRONG_BEAR"
    assert verdict.veto == True

def test_smc_override():
    checker = IndexAlignmentChecker()
    ohlcv_5m = create_mock_ohlcv('bearish', 100)
    ohlcv_15m = create_mock_ohlcv('bearish', 50)
    ctx = IndexContext("NIFTY", ohlcv_5m, ohlcv_15m, 22100.0, "TRENDING")
    
    # RELIANCE has beta 1.15 in universe.yaml, which is below high_beta_threshold (1.3)
    verdict = checker.evaluate("RELIANCE", "LONG", ctx, smc_tier="MONEY", index_sweep=True)
    assert verdict.veto == False
    assert verdict.override_applied == "SMC_MONEY_SWEEP_REVERSAL"
    assert verdict.score_delta == 0.3
