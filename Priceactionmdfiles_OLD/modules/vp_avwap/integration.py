import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from modules.vp_avwap.suite import VolumeProfileAVWAPSuite
from modules.vp_avwap.schemas import LevelSet, VPScoreResult

class VolumeProfileAdapter:
    """
    Adapter to plug VolumeProfileAVWAPSuite into existing PriceActionEngine.
    """
    
    def __init__(self, config_path: str = "config/vp_avwap.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.suite = VolumeProfileAVWAPSuite(self.config, Path("data/composites/"))
        
    def get_vp_levels(self, symbol: str, mtf_analyses: Dict[str, Any], 
                      df_1m: pd.DataFrame, atr_5m: float) -> LevelSet:
        """
        Calculates levels for the current symbol and state.
        """
        # In a real setup, we'd have historical_1m passed in. 
        # For the adapter, we use what's available.
        # FIX: Explicit guardrail for missing data
        if df_1m is None or df_1m.empty:
            raise ValueError(
                f"Intraday 1m data for {symbol} is missing or empty. "
                "Module 2 requires live price flow for real-time VWAP and IB calculations."
            )
        
        prior_ohlc = {} # Should be fetched from data layer
        if not df_1m.empty:
            prior_ohlc['close'] = df_1m['close'].iloc[0] # Very simplified
            
        return self.suite.compute_levels(
            symbol=symbol,
            intraday_1m=df_1m,
            historical_1m=pd.DataFrame(), # Not used for intraday compute, only for refresh
            prior_session_ohlc=prior_ohlc,
            atr_5m=atr_5m
        )

    def score_and_merge(self, signal: Dict[str, Any], level_set: LevelSet, 
                        regime: str, atr_5m: float) -> Dict[str, Any]:
        """
        Applies VP scoring to a candidate signal.
        """
        direction = "LONG" if signal['trade'] == 'CE' else "SHORT"
        
        vp_result = self.suite.score_signal(
            signal_entry_price=signal['entry'],
            signal_direction=direction,
            level_set=level_set,
            regime=regime,
            atr_5m=atr_5m
        )
        
        # Update signal dict
        signal['checklist_score'] += vp_result.regime_weighted_score
        signal['reasons'].append(f"VP/VWAP: {vp_result.reasoning}")
        signal['vp_metadata'] = vp_result
        
        return signal
