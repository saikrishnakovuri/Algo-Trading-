import yaml
import pandas as pd
from typing import Dict, Any, List, Optional
from modules.smc.engine import SmartMoneyConceptsEngine
from modules.smc.schemas import SMCState, SMCScoreResult
from modules.vp_avwap.schemas import LevelSet, ConfluenceLevel

class SMCAdapter:
    """
    Adapter to plug SmartMoneyConceptsEngine into existing PriceActionEngine.
    """
    
    def __init__(self, config_path: str = "config/smc.yaml"):
        self.engine = SmartMoneyConceptsEngine(config_path)
        
    def get_smc_state(self, symbol: str, mtf_analyses: Dict[str, Any], 
                      prior_ohlc: Dict[str, float], preopen_range: Dict[str, float]) -> SMCState:
        
        df_5m = mtf_analyses.get('5m')
        df_1m = mtf_analyses.get('1m')
        
        from modules.price_action_engine import PriceActionEngine
        atr_5m = PriceActionEngine.calculate_atr(df_5m)
        atr_1m = PriceActionEngine.calculate_atr(df_1m)
        
        return self.engine.update(
            symbol=symbol,
            ohlcv_5m=df_5m,
            ohlcv_1m=df_1m,
            prior_session_ohlc=prior_ohlc,
            preopen_range=preopen_range,
            atr_5m=atr_5m,
            atr_1m=atr_1m
        )

    def score_and_merge(self, signal: Dict[str, Any], smc_state: SMCState, 
                        level_set: LevelSet, regime: str, atr_5m: float) -> Dict[str, Any]:
        """
        Applies SMC scoring to a candidate signal.
        """
        direction = "LONG" if signal['trade'] == 'CE' else "SHORT"
        
        smc_result = self.engine.score_signal(
            candidate_entry=signal['entry'],
            candidate_direction=direction,
            smc_state=smc_state,
            level_set=level_set,
            regime=regime,
            atr_5m=atr_5m
        )
        
        # Update signal dict
        signal['checklist_score'] += smc_result.regime_weighted_score
        signal['reasons'].append(f"SMC: {smc_result.reasoning} (Tier: {smc_result.tier_label})")
        signal['smc_metadata'] = smc_result
        
        return signal

def merge_with_smc(confluence_levels: List[ConfluenceLevel], smc_state: SMCState, atr_5m: float) -> List[ConfluenceLevel]:
    """
    Extends ConfluenceLevels with SMC footprints (OBs, FVGs).
    """
    from modules.vp_avwap.level_merger import LevelMerger
    # Create dummy config for LevelMerger
    merger = LevelMerger({'merger': {'cluster_distance_atr': 0.15}})
    
    raw_smc = []
    
    # Order Blocks as levels
    all_obs = smc_state.order_blocks_5m + smc_state.order_blocks_1m
    for ob in all_obs:
        if ob.status != "INVALIDATED":
            raw_smc.append({
                'price': (ob.ob_high + ob.ob_low) / 2.0,
                'type': f"OB_{ob.timeframe}_{ob.direction}",
                'strength': ob.strength
            })
            
    # FVGs as levels (midpoint)
    all_fvgs = smc_state.fvgs_5m + smc_state.fvgs_1m
    for f in all_fvgs:
        if f.status != "FILLED":
            raw_smc.append({
                'price': (f.fvg_high + f.fvg_low) / 2.0,
                'type': f"FVG_{f.timeframe}_{f.direction}",
                'strength': f.strength
            })
            
    # Merge existing confluence levels back to raw format to re-cluster
    raw_existing = []
    for cl in confluence_levels:
        raw_existing.append({
            'price': cl.price,
            'type': list(cl.source_types)[0], # Simplified
            'strength': cl.strength
        })
        
    return merger.merge(raw_existing + raw_smc, atr_5m)
