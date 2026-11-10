import yaml
from typing import Dict, Any, List, Optional
from modules.intermarket.schemas import GlobalRiskVerdict

class GlobalRiskContext:
    def __init__(self, config_path: str = "config/intermarket.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['global_risk']

    def evaluate(self, snapshot: Dict[str, float], fii_flow: float = 0.0, dii_flow: float = 0.0) -> GlobalRiskVerdict:
        """
        snapshot: { 'SPY': 0.005, 'QQQ': 0.006, ... } returns as pct
        """
        c = self.config
        up_count = sum(1 for v in snapshot.values() if v >= c['risk_on']['min_pct'] / 100)
        down_count = sum(1 for v in snapshot.values() if v <= -c['risk_off']['min_pct'] / 100)
        
        sentiment = "NEUTRAL"
        score_delta = 0.0
        veto = False
        
        if up_count >= c['risk_on_broad']['min_indices_up']:
            sentiment = "RISK_ON_BROAD"
            score_delta = c['score_deltas_window_a']['risk_on_broad_aligned']
        elif up_count >= c['risk_on']['min_indices_up']:
            sentiment = "RISK_ON"
            score_delta = c['score_deltas_window_a']['risk_on_aligned']
        elif down_count >= c['risk_off_broad']['min_indices_up']: # reuse min_indices_up for down count
            sentiment = "RISK_OFF_BROAD"
            score_delta = c['score_deltas_window_a']['risk_off_broad_contra']
            veto = True # Require ELITE tier for LONGs, simplified here
        elif down_count >= c['risk_off']['min_indices_down']:
            sentiment = "RISK_OFF"
            score_delta = c['score_deltas_window_a']['risk_off_contra']

        reasoning = f"Sentiment: {sentiment} | Global Up: {up_count} | Down: {down_count}"
        
        return GlobalRiskVerdict(
            sentiment=sentiment,
            global_indices_snapshot=snapshot,
            fii_flow_prior_day=fii_flow,
            dii_flow_prior_day=dii_flow,
            fii_dii_divergence=False, # Placeholder
            score_delta=score_delta,
            veto=veto,
            reasoning=reasoning
        )
