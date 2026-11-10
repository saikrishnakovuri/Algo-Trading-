import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from modules.risk_exec.schemas import TrailUpdate, OpenPosition, MarketContext

class AdaptiveTrailingEngine:
    """
    Manages a 4-stage adaptive stop-loss trailing logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['trailing']
        
    def check_trail(self, position: OpenPosition, context: MarketContext, 
                    current_high: float, current_low: float) -> Optional[TrailUpdate]:
        
        stage = position.trail_stage
        entry = position.entry_price
        dist = abs(entry - position.current_sl) # wait, position doesn't store initial SL? 
        # I should use per_share_risk from metadata
        r = position.metadata.get('per_share_risk', dist)
        if r <= 0: return None
        
        new_sl = position.current_sl
        new_stage = stage
        trigger = ""
        
        # Stage 1 -> 2 (0.3R)
        if stage == 1:
            move_r = 0.3
            if position.direction == "LONG" and (current_high - entry) >= move_r * r:
                new_stage = 2
                new_sl = entry - 0.7 * r
                trigger = "PRE_BE_0.3R"
            elif position.direction == "SHORT" and (entry - current_low) >= move_r * r:
                new_stage = 2
                new_sl = entry + 0.7 * r
                trigger = "PRE_BE_0.3R"

        # Stage 2 -> 3 (0.5R BE)
        if new_stage == 2:
            move_r = 0.5
            tick = 0.05
            if position.direction == "LONG" and (current_high - entry) >= move_r * r:
                new_stage = 3
                new_sl = entry + tick
                trigger = "BE_0.5R"
            elif position.direction == "SHORT" and (entry - current_low) >= move_r * r:
                new_stage = 3
                new_sl = entry - tick
                trigger = "BE_0.5R"

        # Stage 3 -> 4 (T1 hit or 1.2R)
        if new_stage == 3:
            t1_hit = position.qty_remaining < position.qty_initial
            r_trigger = 1.2
            current_r = (current_high - entry) / r if position.direction == "LONG" else (entry - current_low) / r
            
            if t1_hit or current_r >= r_trigger:
                new_stage = 4
                trigger = "DYNAMIC_TRAIL_START"
                # Initial stage 4 sl
                if context.regime.startswith("TRENDING"):
                    # ATR chandelier
                    mult = self.config['chandelier_atr_multiplier']
                    if position.direction == "LONG":
                        new_sl = current_high - mult * context.atr_5m
                    else:
                        new_sl = current_low + mult * context.atr_5m
                else:
                    # Structure based
                    smc = context.smc_state
                    if smc and hasattr(smc, 'structure'):
                        struct = smc.structure
                        if position.direction == "LONG":
                            new_sl = struct.last_swing_HL or position.current_sl
                        else:
                            new_sl = struct.last_swing_LH or position.current_sl
        
        # Stage 4 Active: Progressive Trail
        if stage == 4:
            if context.regime.startswith("TRENDING"):
                mult = self.config['chandelier_atr_multiplier']
                cand_sl = current_high - mult * context.atr_5m if position.direction == "LONG" else current_low + mult * context.atr_5m
                if position.direction == "LONG" and cand_sl > position.current_sl:
                    new_sl = cand_sl
                    trigger = "ATR_CHANDELIER_UPDATE"
                elif position.direction == "SHORT" and cand_sl < position.current_sl:
                    new_sl = cand_sl
                    trigger = "ATR_CHANDELIER_UPDATE"
            else:
                smc = context.smc_state
                if smc and hasattr(smc, 'structure'):
                    struct = smc.structure
                    cand_sl = struct.last_swing_HL if position.direction == "LONG" else struct.last_swing_LH
                    if cand_sl:
                        if position.direction == "LONG" and cand_sl > position.current_sl:
                            new_sl = cand_sl
                            trigger = "STRUCTURE_TRAIL_UPDATE"
                        elif position.direction == "SHORT" and cand_sl < position.current_sl:
                            new_sl = cand_sl
                            trigger = "STRUCTURE_TRAIL_UPDATE"

        if new_stage != stage or abs(new_sl - position.current_sl) > 0.01:
            # Ensure no adverse move
            if position.direction == "LONG":
                new_sl = max(new_sl, position.current_sl)
            else:
                new_sl = min(new_sl, position.current_sl)
                
            return TrailUpdate(
                stage=new_stage,
                new_sl=round(float(new_sl), 2),
                trigger=trigger,
                timestamp=datetime.now()
            )
            
        return None
