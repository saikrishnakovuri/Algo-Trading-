import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from modules.risk_exec.sizer import AdaptivePositionSizer
from modules.risk_exec.schemas import ApprovedSignal

def test_kelly_excludes_open_trades(tmp_path):
    # Setup mock trade history with mixed statuses using CSV to bypass pyarrow issues
    history_file = tmp_path / "trade_history.csv"
    
    data = {
        'symbol': ['RELIANCE', 'RELIANCE', 'RELIANCE', 'INFY', 'INFY'],
        'regime': ['TRENDING_LOW_VOL', 'TRENDING_LOW_VOL', 'TRENDING_LOW_VOL', 'TRENDING_LOW_VOL', 'TRENDING_LOW_VOL'],
        'net_r': [2.0, -1.0, 1.5, 0.5, -0.2], 
        'status': ['CLOSED', 'CLOSED', 'CLOSED', 'OPEN', 'OPEN']
    }
    df = pd.DataFrame(data)
    df.to_csv(history_file, index=False)
    
    config = {
        'sizing': {
            'base_risk_pct': {'MONEY': 1.0},
            'kelly': {
                'fraction': 0.25,
                'min_trades_per_regime': 2,
                'lookback_trades': 100,
                'min_multiplier': 0.3,
                'max_multiplier': 1.5
            },
            'volatility_target': {'target_annualised_pct': 15},
            'constraints': {'position_cap_pct': 20, 'liquidity_cap_of_adv': 0.002}
        }
    }
    
    sizer = AdaptivePositionSizer(config, history_file)
    mult = sizer._calculate_kelly_multiplier('TRENDING_LOW_VOL')
    
    assert mult == pytest.approx(0.3)
