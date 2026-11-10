import yaml
from typing import Dict, List, Any, Optional
from modules.intermarket.schemas import IntermarketVerdict
from datetime import datetime

class IntermarketAggregator:
    def __init__(self, config_path: str = "config/intermarket.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['aggregator']

    def aggregate(self, sub_verdicts: Dict[str, Any], 
                  regime: str, setup_type: str, 
                  active_window: str) -> IntermarketVerdict:
        
        veto_reasons = []
        raw_combined_delta = 0.0
        allow = True
        
        # Check all for VETOs and sum deltas
        for engine_name, verdict in sub_verdicts.items():
            if hasattr(verdict, 'veto') and verdict.veto:
                allow = False
                veto_reasons.append(f"{engine_name}: {verdict.reasoning}")
            
            if hasattr(verdict, 'score_delta'):
                raw_combined_delta += verdict.score_delta

        # Cap raw delta
        cap_min, cap_max = self.config['raw_delta_cap']
        raw_combined_delta = max(cap_min, min(cap_max, raw_combined_delta))
        
        # 1. Regime Weighting
        regime_weight = self.config['regime_weights'].get(regime, 1.0)
        regime_weighted_delta = raw_combined_delta * regime_weight
        
        # 2. Setup Weighting
        setup_weight = self.config['setup_weights'].get(setup_type, 1.0)
        
        # 3. Window Weighting
        window_weight = self.config['window_weights'].get(active_window, 1.0)
        
        final_delta = regime_weighted_delta * setup_weight * window_weight
        
        reasoning = f"Raw: {raw_combined_delta:.2f} | Final: {final_delta:.2f} | R-Weight: {regime_weight} | S-Weight: {setup_weight} | W-Weight: {window_weight}"
        
        return IntermarketVerdict(
            allow=allow,
            raw_combined_delta=raw_combined_delta,
            regime_weighted_delta=regime_weighted_delta,
            final_delta=final_delta,
            veto_reasons=veto_reasons,
            sub_verdicts=sub_verdicts,
            reasoning=reasoning,
            evaluated_at=datetime.now()
        )
