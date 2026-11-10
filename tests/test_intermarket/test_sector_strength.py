import pytest
import pandas as pd
import numpy as np
from modules.intermarket.sector_strength import SectorStrengthAnalyzer

def create_mock_sector_data(return_pct: float):
    base = 10000.0
    curr = base * (1 + return_pct/100)
    df = pd.DataFrame({
        'Open': [base], 'High': [max(base, curr)], 'Low': [min(base, curr)], 'Close': [curr]
    })
    return df

def test_sector_ranking():
    checker = SectorStrengthAnalyzer()
    
    nifty_df = create_mock_sector_data(1.0) # Nifty up 1%
    # 12 sectors to make quartiles clear (top 3 = leaders)
    sector_indices = {
        "NIFTY_BANK": create_mock_sector_data(2.5),
        "S2": create_mock_sector_data(2.4),
        "S3": create_mock_sector_data(2.3),
        "S4": create_mock_sector_data(1.5),
        "S5": create_mock_sector_data(1.4),
        "NIFTY_IT": create_mock_sector_data(1.0),
        "S7": create_mock_sector_data(0.8),
        "S8": create_mock_sector_data(0.5),
        "S9": create_mock_sector_data(0.2),
        "S10": create_mock_sector_data(-0.1),
        "S11": create_mock_sector_data(-0.3),
        "NIFTY_AUTO": create_mock_sector_data(-0.5)
    }
    
    universe_snapshot = {
        "ICICIBANK": {"open": 1000, "close": 1010}, # Aligned with LONG
        "SBIN": {"open": 600, "close": 605}          # Aligned with LONG
    }
    
    # HDFCBANK is in NIFTY_BANK
    verdict = checker.evaluate("HDFCBANK", "LONG", sector_indices, nifty_df, universe_snapshot)
    
    assert verdict.classification == "LEADERS"
    assert verdict.sector_rank == 1
    assert verdict.peer_breadth_aligned == 2
    assert verdict.score_delta > 0.5 # 0.6 from leader
