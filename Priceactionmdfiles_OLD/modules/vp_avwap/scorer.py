from typing import Dict, Any, List, Optional
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any
from modules.vp_avwap.schemas import ConfluenceLevel, VPScoreResult

class VPSignalScorer:
    """
    Scores signals based on Volume Profile and VWAP confluence.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['scoring']
        
    def score(self, entry_price: float, direction: Literal["LONG", "SHORT"], 
              level_set: Any, regime: str, atr_5m: float) -> VPScoreResult:
        
        bonus = 0.0
        penalties = 0.0
        reasons = []
        
        # 1. Find nearest confluence level
        nearest_level = None
        min_dist_atr = float('inf')
        
        for lvl in level_set.confluence_levels:
            dist = abs(entry_price - lvl.price)
            dist_atr = dist / atr_5m
            if dist_atr < min_dist_atr:
                min_dist_atr = dist_atr
                nearest_level = lvl
                
        # 2. Confluence Bonuses
        bonus_val = 0.0
        if nearest_level and min_dist_atr <= 0.3:
            conf_count = nearest_level.confluence_count
            strength = nearest_level.strength
            
            b_cfg = self.config['confluence_bonuses']
            if min_dist_atr <= 0.1 and conf_count >= 3 and strength >= 0.8:
                bonus_val = b_cfg['triple_elite']
                reasons.append(f"Triple Elite Confluence at {nearest_level.price} ({min_dist_atr:.2f} ATR)")
            elif conf_count >= 3 and strength >= 0.6:
                bonus_val = b_cfg['triple']
                reasons.append(f"Triple Confluence ({min_dist_atr:.2f} ATR)")
            elif conf_count >= 2 and strength >= 0.5:
                bonus_val = b_cfg['double']
                reasons.append(f"Double Confluence ({min_dist_atr:.2f} ATR)")
            elif conf_count == 1:
                # Check if it's an elite single source
                elites = {'POC', 'VAH', 'VAL', 'AVWAP_PDH', 'Session_Open'}
                if any(e in nearest_level.source_types for e in elites):
                    bonus_val = b_cfg['single_elite']
                    reasons.append(f"Elite Level Contact: {list(nearest_level.source_types)[0]}")
        
        # 3. Penalties
        p_cfg = self.config['penalties']
        
        # Penalty: INSIDE LVN
        for lvn in level_set.session_vp.get('LVNs', []):
            if abs(entry_price - lvn['price']) / atr_5m < 0.1:
                penalties += p_cfg['in_lvn']
                reasons.append("Entry inside Low Volume Node (Price Vacuum)")
                break
                
        # Penalty: Counter-trend in trending regime
        if regime.startswith("TRENDING_"):
            session_vwap = level_set.avwaps.get('Session_Open', {}).get('value')
            if session_vwap:
                if direction == "LONG" and entry_price < session_vwap:
                    penalties += p_cfg['counter_session_avwap_in_trend']
                    reasons.append("Counter-trend entry (Below Session VWAP in Trend)")
                elif direction == "SHORT" and entry_price > session_vwap:
                    penalties += p_cfg['counter_session_avwap_in_trend']
                    reasons.append("Counter-trend entry (Above Session VWAP in Trend)")

        # Penalty: Chase into supply (Long above VAH in mean-reversion)
        if regime == "MEAN_REVERTING":
            vah = level_set.session_vp.get('VAH')
            val = level_set.session_vp.get('VAL')
            if direction == "LONG" and vah and entry_price > vah:
                penalties += p_cfg['chase_into_supply']
                reasons.append("Chasing long above Value Area High in Mean Reversion")
            elif direction == "SHORT" and val and entry_price < val:
                penalties += p_cfg['chase_into_supply']
                reasons.append("Chasing short below Value Area Low in Mean Reversion")

        # Combine
        raw_score = bonus_val + penalties
        raw_score = max(-2.0, raw_score) # Floor
        
        # 4. Regime Weighting
        weight = self.config['regime_weights'].get(regime, 1.0)
        weighted_score = raw_score * weight
        
        return VPScoreResult(
            raw_score=round(raw_score, 2),
            regime_weighted_score=round(weighted_score, 2),
            nearest_confluence=nearest_level,
            distance_to_nearest_atr=round(min_dist_atr, 3),
            reasoning=" | ".join(reasons) if reasons else "No Volume/VWAP Confluence"
        )
