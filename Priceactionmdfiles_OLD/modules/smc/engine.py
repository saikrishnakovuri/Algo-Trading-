import yaml
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any

from modules.smc.schemas import SMCState, SMCScoreResult, OrderBlock, FairValueGap, LiquiditySweep
from modules.smc.order_block import OrderBlockDetector
from modules.smc.fair_value_gap import FairValueGapDetector
from modules.smc.liquidity_sweep import LiquiditySweepDetector
from modules.smc.structure import StructureTracker
from modules.smc.premium_discount import PremiumDiscountCalculator
from modules.smc.scorer import SMCSignalScorer
from modules.vp_avwap.schemas import LevelSet

class SmartMoneyConceptsEngine:
    """
    Orchestrates all SMC analysis components.
    """
    
    def __init__(self, config_path: str = "config/smc.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        self.ob_5m = OrderBlockDetector(self.config, "5m")
        self.ob_1m = OrderBlockDetector(self.config, "1m")
        self.fvg_5m = FairValueGapDetector(self.config, "5m")
        self.fvg_1m = FairValueGapDetector(self.config, "1m")
        self.sweep_1m = LiquiditySweepDetector(self.config, "1m")
        self.sweep_5m = LiquiditySweepDetector(self.config, "5m")
        self.structure_tracker = StructureTracker(self.config)
        self.pd_calculator = PremiumDiscountCalculator(self.config)
        self.scorer = SMCSignalScorer(self.config)
        
    def update(
        self,
        symbol: str,
        ohlcv_5m: pd.DataFrame,
        ohlcv_1m: pd.DataFrame,
        prior_session_ohlc: Dict[str, float],
        preopen_range: Dict[str, float],
        atr_5m: float,
        atr_1m: float,
    ) -> SMCState:
        
        # 1. Update Detectors
        obs_5m = self.ob_5m.update(ohlcv_5m, atr_5m)
        obs_1m = self.ob_1m.update(ohlcv_1m, atr_1m)
        
        fvgs_5m = self.fvg_5m.update(ohlcv_5m, atr_5m)
        fvgs_1m = self.fvg_1m.update(ohlcv_1m, atr_1m)
        
        sweeps_1m = self.sweep_1m.update(ohlcv_1m, atr_1m, prior_session_ohlc, preopen_range)
        sweeps_5m = self.sweep_5m.update(ohlcv_5m, atr_5m, prior_session_ohlc, preopen_range)
        
        # Get invalidated OBs for structure tracker
        invalidated_obs = [ob for ob in obs_5m if ob.status == "INVALIDATED"]
        structure = self.structure_tracker.update(ohlcv_5m, atr_5m, invalidated_obs)
        
        # 2. Premium/Discount
        current_price = float(ohlcv_1m['close'].iloc[-1])
        pd_zones = self.pd_calculator.calculate(current_price, structure)
        
        return SMCState(
            order_blocks_5m=obs_5m,
            order_blocks_1m=obs_1m,
            fvgs_5m=fvgs_5m,
            fvgs_1m=fvgs_1m,
            active_sweeps=sweeps_1m + sweeps_5m,
            structure=structure,
            premium_discount=pd_zones,
            computed_at=datetime.now()
        )
    
    def score_signal(
        self,
        candidate_entry: float,
        candidate_direction: Literal["LONG", "SHORT"],
        smc_state: SMCState,
        level_set: LevelSet,
        regime: str,
        atr_5m: float,
    ) -> SMCScoreResult:
        return self.scorer.score(candidate_entry, candidate_direction, smc_state, level_set, regime, atr_5m)
