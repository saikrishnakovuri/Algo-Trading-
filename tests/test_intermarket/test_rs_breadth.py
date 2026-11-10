import pytest
import pandas as pd
from datetime import datetime
from modules.intermarket.relative_strength import RelativeStrengthScorer
from modules.intermarket.breadth import BreadthEngine
from modules.intermarket.schemas import UniverseSnapshot

def test_relative_strength():
    scorer = RelativeStrengthScorer()
    
    nifty_df = pd.DataFrame({'Open': [22000], 'Close': [22000]}) # Nifty flat
    stock_df = pd.DataFrame({'Open': [1000], 'Close': [1050]})   # Stock up 5%
    
    # Mock universe: 10 stocks, all flat except one
    symbol_snapshots = {f"S{i}": {'open': 100, 'close': 100, 'vwap': 100} for i in range(10)}
    symbol_snapshots["RELIANCE"] = {'open': 1000, 'close': 1050, 'vwap': 1000}
    
    universe_snap = UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots=symbol_snapshots)
    
    verdict = scorer.evaluate("RELIANCE", "LONG", stock_df, nifty_df, universe_snap)
    
    assert verdict.classification == "SUPER_STRONG"
    assert verdict.rs_percentiles['session'] > 90
    assert verdict.score_delta == 0.8

def test_breadth_bullish():
    engine = BreadthEngine()
    
    # 8 advancers, 2 decliners
    symbol_snapshots = {f"A{i}": {'open': 100, 'close': 110, 'volume': 1000, 'vwap': 100} for i in range(8)}
    symbol_snapshots.update({f"D{i}": {'open': 100, 'close': 90, 'volume': 500, 'vwap': 100} for i in range(2)})
    
    universe_snap = UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots=symbol_snapshots)
    
    verdict = engine.evaluate("LONG", universe_snap)
    assert verdict.regime == "BULLISH_BROAD"
    assert verdict.adr == 4.0
    assert verdict.score_delta == 0.4
