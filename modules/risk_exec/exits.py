import numpy as np
from typing import Dict, Any, List, Optional
from modules.risk_exec.schemas import ExitPlan, Target, ApprovedSignal, MarketContext

class MultiTargetExitPlanner:
    """
    Computes a 3-tier scale-out plan using context-driven levels as anchors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['exits']
        
    def calculate(self, signal: ApprovedSignal, context: MarketContext, 
                  per_share_risk: float) -> ExitPlan:
        
        entry = signal.entry_price
        direction = signal.direction
        r = per_share_risk
        
        # 1. Gather Candidate Levels
        candidates = []
        
        # From Volume Profile (Module 2)
        if hasattr(context.level_set, 'confluence_levels'):
            for lvl in context.level_set.confluence_levels:
                candidates.append({'price': lvl.price, 'source': list(lvl.source_types)[0], 'strength': lvl.strength})
                
        # From SMC (Module 3)
        smc = context.smc_state
        if smc:
            for ob in (smc.order_blocks_5m + smc.order_blocks_1m):
                if ob.direction != ( "BULL" if direction == "LONG" else "BEAR"): # Opposite OB is a target
                    candidates.append({'price': (ob.ob_high + ob.ob_low)/2.0, 'source': 'SMC_OB', 'strength': ob.strength})
            for fvg in (smc.fvgs_5m + smc.fvgs_1m):
                if fvg.direction != ("BULL" if direction == "LONG" else "BEAR"):
                    candidates.append({'price': (fvg.fvg_high + fvg.fvg_low)/2.0, 'source': 'SMC_FVG', 'strength': fvg.strength})
                    
        # Filter by direction and max distance (4R)
        if direction == "LONG":
            valid = [c for c in candidates if c['price'] > entry and c['price'] <= entry + 4.0*r]
            valid = sorted(valid, key=lambda x: x['price'])
        else:
            valid = [c for c in candidates if c['price'] < entry and c['price'] >= entry - 4.0*r]
            valid = sorted(valid, key=lambda x: x['price'], reverse=True)
            
        # 2. Select 3 Targets
        targets = []
        
        # T1: Closest >= 0.8R
        t1_cands = [c for c in valid if abs(c['price'] - entry) >= self.config['t1_min_r'] * r]
        if t1_cands:
            t1 = t1_cands[0]
            targets.append(Target(t1['price'], abs(t1['price']-entry)/r, 0.0, t1['source']))
        else:
            targets.append(Target(entry + 1.0*r if direction=="LONG" else entry - 1.0*r, 1.0, 0.0, "Fixed_1R"))
            
        # T2: 1.6R - 2.5R
        t2_cands = [c for c in valid if self.config['t2_range_r'][0]*r <= abs(c['price'] - entry) <= self.config['t2_range_r'][1]*r]
        if t2_cands:
            t2 = t2_cands[0]
            targets.append(Target(t2['price'], abs(t2['price']-entry)/r, 0.0, t2['source']))
        else:
            targets.append(Target(entry + 2.0*r if direction=="LONG" else entry - 2.0*r, 2.0, 0.0, "Fixed_2R"))

        # T3: 3R+
        t3_cands = [c for c in valid if abs(c['price'] - entry) >= self.config['t3_min_r'] * r]
        if t3_cands:
            t3 = t3_cands[0]
            targets.append(Target(t3['price'], abs(t3['price']-entry)/r, 0.0, t3['source']))
        else:
            targets.append(Target(entry + 3.5*r if direction=="LONG" else entry - 3.5*r, 3.5, 0.0, "Fixed_3.5R"))

        # 3. Allocation
        alloc = self.config['allocations'].get(context.regime, [0.33, 0.33, 0.34])
        
        # Override by setup type
        if signal.setup_type == "TRAP_FADE":
            alloc = self.config['allocations']['MEAN_REVERTING']
        elif signal.setup_type == "TREND_CONTINUATION":
            alloc = [0.25, 0.35, 0.40] # Trending profile
            
        for i, t in enumerate(targets):
            t.size_pct = alloc[i] if i < len(alloc) else 0.0
            
        return ExitPlan(
            targets=[t for t in targets if t.size_pct > 0],
            allocation_profile=str(alloc),
            reasoning=f"Targets anchored to {', '.join([t.level_source for t in targets])}"
        )
