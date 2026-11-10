import numpy as np
import pandas as pd
try:
    from typing import Dict, Any, List, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, List, Optional, Union
    Literal = Any
from modules.risk_exec.schemas import SLDecision, ApprovedSignal, MarketContext

class VolatilityAdaptiveStopLoss:
    """
    Computes context-aware SL by picking the widest among three candidates.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['stop_loss']
        
    def calculate(self, signal: ApprovedSignal, context: MarketContext, 
                  zone_low: float, zone_high: float) -> SLDecision:
        
        atr = context.atr_5m
        regime = context.regime
        tick_size = 0.05
        
        # 1. Candidate A: Zone-based
        buffer_a_mult = self.config['zone_buffer_atr_by_regime'].get(regime, 0.25)
        buffer_a = buffer_a_mult * atr
        
        if signal.direction == "LONG":
            sl_a = zone_low - buffer_a
        else:
            sl_a = zone_high + buffer_a
            
        # 2. Candidate B: Structure-based (from Module 3)
        buffer_b = self.config['structure_buffer_atr'] * atr
        sl_b = sl_a # fallback
        
        smc = context.smc_state
        if smc and hasattr(smc, 'structure'):
            struct = smc.structure
            if signal.direction == "LONG":
                swing_low = struct.last_swing_HL or struct.last_swing_LL
                if swing_low: sl_b = swing_low - buffer_b
            else:
                swing_high = struct.last_swing_LH or struct.last_swing_HH
                if swing_high: sl_b = swing_high + buffer_b

        # 3. Candidate C: Chandelier (Volatility-floor)
        mult_c = self.config['chandelier_atr_multiplier'].get(regime, 2.0)
        buffer_c = mult_c * atr
        if signal.direction == "LONG":
            sl_c = signal.entry_price - buffer_c
        else:
            sl_c = signal.entry_price + buffer_c
            
        # 4. Pick widest
        candidates = {'zone': sl_a, 'structure': sl_b, 'chandelier': sl_c}
        if signal.direction == "LONG":
            sl_final = min(sl_a, sl_b, sl_c)
            chosen = min(candidates, key=candidates.get)
        else:
            sl_final = max(sl_a, sl_b, sl_c)
            chosen = max(candidates, key=candidates.get)
            
        # 5. Guardrails
        guardrails_hit = []
        dist = abs(signal.entry_price - sl_final)
        
        min_dist = self.config['min_sl_distance_atr'] * atr
        if dist < min_dist:
            dist = min_dist
            sl_final = signal.entry_price - dist if signal.direction == "LONG" else signal.entry_price + dist
            guardrails_hit.append("MIN_DIST")
            
        max_sl_mult = self.config['max_sl_distance_atr']
        if isinstance(max_sl_mult, dict):
            max_sl_mult = max_sl_mult.get(regime, 2.5)
            
        max_dist = max_sl_mult * atr
        if dist > max_dist:
            guardrails_hit.append("SL_TOO_WIDE")
            
        # Round to tick size
        if signal.direction == "LONG":
            sl_final = np.floor(sl_final / tick_size) * tick_size
        else:
            sl_final = np.ceil(sl_final / tick_size) * tick_size
            
        return SLDecision(
            sl_price=round(float(sl_final), 2),
            per_share_risk=round(abs(signal.entry_price - sl_final), 2),
            candidates={k: round(v, 2) for k, v in candidates.items()},
            chosen=chosen,
            distance_atr=round(dist / atr, 2),
            guardrails_hit=guardrails_hit,
            reasoning=f"Selected {chosen} stop (Widest of 3). Distance {dist/atr:.2f} ATR."
        )
