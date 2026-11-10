import pytest
import pandas as pd
from datetime import datetime
from modules.intermarket.breadth import BreadthEngine
from modules.intermarket.schemas import UniverseSnapshot

def test_breadth_excludes_candidate_symbol():
    engine = BreadthEngine()
    
    # Setup: 4 stocks. 
    # A, B, C are advancers.
    # RELIANCE is a decliner.
    symbol_snapshots = {
        "A": {'open': 100, 'close': 110, 'volume': 1000, 'vwap': 100},
        "B": {'open': 100, 'close': 110, 'volume': 1000, 'vwap': 100},
        "C": {'open': 100, 'close': 110, 'volume': 1000, 'vwap': 100},
        "RELIANCE": {'open': 100, 'close': 90, 'volume': 5000, 'vwap': 100}
    }
    
    universe_snap = UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots=symbol_snapshots)
    
    # When calculating breadth FOR RELIANCE, it should be excluded.
    # Remaining: A, B, C (all advancers). ADR should be 3/0 -> 3.0
    verdict = engine.evaluate("LONG", universe_snap, candidate_symbol="RELIANCE")
    
    assert verdict.adr == 3.0
    assert "Regime: BULLISH_BROAD" in verdict.reasoning # 3 adv, 0 dec is broad bullish
    
    # When calculating breadth FOR A, A should be excluded.
    # Remaining: B, C (adv), RELIANCE (dec). ADR should be 2/1 = 2.0
    verdict_a = engine.evaluate("LONG", universe_snap, candidate_symbol="A")
    assert verdict_a.adr == 2.0
