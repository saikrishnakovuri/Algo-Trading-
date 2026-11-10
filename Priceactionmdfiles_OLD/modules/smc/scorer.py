from typing import Dict, Any, List, Optional
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any
from modules.smc.schemas import SMCState, SMCScoreResult, OrderBlock, FairValueGap, LiquiditySweep
from modules.vp_avwap.schemas import LevelSet

class SMCSignalScorer:
    """
    Evaluates SMC footprints against a candidate signal and assigns a conviction score.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['smc']['scoring']
        
    def score(self, entry_price: float, direction: Literal["LONG", "SHORT"], 
              smc_state: SMCState, level_set: LevelSet, regime: str, atr_5m: float) -> SMCScoreResult:
        
        bonuses: List[float] = []
        penalties: float = 0.0
        aligned: List[str] = []
        
        # 1. Identify active footprints
        active_obs = smc_state.order_blocks_5m + smc_state.order_blocks_1m
        active_fvgs = smc_state.fvgs_5m + smc_state.fvgs_1m
        active_sweeps = smc_state.active_sweeps
        
        # 2. MATCHING LOGIC
        
        # A. Liquidity Sweeps (Highest priority)
        relevant_sweep = None
        for s in active_sweeps:
            # If LONG, we want a Low Sweep (PDL, SL, etc.)
            is_low_sweep = "L" in s.pool_type or s.pool_type == "SL"
            is_high_sweep = "H" in s.pool_type or s.pool_type == "SH"
            
            if direction == "LONG" and is_low_sweep:
                relevant_sweep = s; break
            if direction == "SHORT" and is_high_sweep:
                relevant_sweep = s; break
                
        # B. Order Blocks
        near_ob = False
        for ob in active_obs:
            if ob.status == "INVALIDATED": continue
            dist = abs(entry_price - (ob.ob_high + ob.ob_low)/2.0)
            if dist < 0.2 * atr_5m:
                if (direction == "LONG" and ob.direction == "BULL") or \
                   (direction == "SHORT" and ob.direction == "BEAR"):
                    near_ob = True; break
                    
        # C. Structure Alignment
        struct_aligned = (direction == "LONG" and smc_state.structure.current_state == "UPTREND") or \
                         (direction == "SHORT" and smc_state.structure.current_state == "DOWNTREND")
                         
        # 3. SCORING RUBRIC
        
        # Tier 3.5: MONEY PATTERN
        if relevant_sweep and relevant_sweep.tier <= 2 and near_ob and smc_state.structure.last_CHoCH:
             # Simplified check for 20 bar window on CHoCH
             # If all match, append 3.5
             bonuses.append(self.config.get('money_pattern', 3.5))
             aligned.append("MONEY PATTERN: Sweep + OB + CHoCH")
             
        # Tier 2.5: ELITE SMC
        elif relevant_sweep and near_ob:
            bonuses.append(self.config.get('elite', 2.5))
            aligned.append("ELITE: Sweep + OB Confluence")
            
        # Tier 1.8: STRONG SMC
        elif near_ob and struct_aligned:
            bonuses.append(self.config.get('strong', 1.8))
            aligned.append("STRONG: OB + Structure Alignment")
            
        # Tier 1.2: GOOD SMC
        elif near_ob:
            bonuses.append(self.config.get('good', 1.2))
            aligned.append("GOOD: OB Support/Resistance")
            
        # Tier 0.6: MINOR SMC
        elif any(f.direction == ("BULL" if direction == "LONG" else "BEAR") for f in active_fvgs):
            bonuses.append(self.config.get('minor', 0.6))
            aligned.append("MINOR: FVG Magnet")

        # 4. PENALTIES
        p_cfg = self.config['penalties']
        
        # Penalty: Against MSS
        mss = smc_state.structure.last_MSS
        if mss:
            if (direction == "LONG" and mss['direction'] == 'BEAR') or \
               (direction == "SHORT" and mss['direction'] == 'BULL'):
                penalties += p_cfg['against_mss']
                aligned.append("PENALTY: Against Market Structure Shift")
                
        # Penalty: Chasing Premium/Discount
        zone = smc_state.premium_discount.get('zone')
        if not relevant_sweep:
            if direction == "LONG" and zone == "PREMIUM":
                penalties += p_cfg['chasing_premium_discount']
                aligned.append("PENALTY: Buying in Premium Zone")
            elif direction == "SHORT" and zone == "DISCOUNT":
                penalties += p_cfg['chasing_premium_discount']
                aligned.append("PENALTY: Selling in Discount Zone")

        raw_score = max(bonuses) if bonuses else 0.0
        raw_score += penalties
        raw_score = max(-2.0, min(3.5, raw_score))
        
        # 5. Regime Weighting
        weight = self.config['regime_weights'].get(regime, 1.0)
        weighted_score = raw_score * weight
        
        # Tier Label
        if raw_score >= 3.0: tier = "MONEY"
        elif raw_score >= 2.0: tier = "ELITE"
        elif raw_score >= 1.5: tier = "STRONG"
        elif raw_score >= 1.0: tier = "GOOD"
        elif raw_score >= 0.5: tier = "MINOR"
        elif raw_score < 0: tier = "PENALISED"
        else: tier = "NONE"
        
        return SMCScoreResult(
            raw_score=round(raw_score, 2),
            regime_weighted_score=round(weighted_score, 2),
            tier_label=tier,
            aligned_footprints=aligned,
            reasoning=" | ".join(aligned) if aligned else "No significant SMC footprints"
        )
