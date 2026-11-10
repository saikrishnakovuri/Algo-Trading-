import yaml
import os
from datetime import datetime
from typing import Dict, Any, Tuple
from modules.regime.schemas import RegimeDecision

class RuleBasedClassifier:
    """
    Layer 1: Deterministic rule-based market regime classification.
    """
    
    def __init__(self, config_path: str = "config/regime.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)['regime']

    def classify(self, features: Dict[str, float]) -> RegimeDecision:
        # Extract features for readability
        adx = features.get("ADX_5m", 0)
        chop = features.get("Choppiness_5m", 50)
        hurst = features.get("Hurst_exponent", 0.5)
        rv_ratio = features.get("RV_ratio", 1.0)
        vix_slope = features.get("VIX_slope", 0)
        range_ratio = features.get("Range_ratio", 1.0)
        
        # Threshods from config
        adx_strong = self.config['adx']['trending_strong']
        adx_weak = self.config['adx']['trending_weak']
        chop_trend = self.config['choppiness']['trend_threshold']
        chop_max = self.config['choppiness']['chop_threshold']
        hurst_trend = self.config['hurst']['trend_threshold']
        hurst_revert = self.config['hurst']['revert_threshold']
        rv_high = self.config['rv_ratio']['high_vol']
        vix_spike = self.config['vix']['spike_pct']

        conditions_met = 0
        total_conditions = 4
        
        # REGIME D: CHOPPY (Highest Priority Safety)
        is_choppy = False
        reason = ""
        if chop > chop_max:
            is_choppy = True
            reason = f"Choppiness ({chop:.1f}) > {chop_max}"
        elif range_ratio < 0.5 and adx < 15:
            is_choppy = True
            reason = f"Low Range ({range_ratio:.2f}) & Low ADX ({adx:.1f})"
        elif vix_slope > vix_spike:
            is_choppy = True
            reason = f"VIX Spike ({vix_slope:.1f}%) > {vix_spike}%"
            
        if is_choppy:
            return RegimeDecision(
                regime="CHOPPY_UNTRADEABLE",
                confidence=1.0,
                allow_trades=False,
                param_overrides=self.config['overrides']['CHOPPY_UNTRADEABLE'],
                feature_snapshot=features,
                reasoning=reason
            )

        # REGIME A: TRENDING HIGH VOL
        # ADX_5m >= 25 AND Choppiness < 38.2 AND Hurst > 0.55 AND RV_ratio > 1.3
        a_score = 0
        if adx >= adx_strong: a_score += 1
        if chop < chop_trend: a_score += 1
        if hurst > hurst_trend: a_score += 1
        if rv_ratio > rv_high: a_score += 1
        
        if a_score >= 3:
            return RegimeDecision(
                regime="TRENDING_HIGH_VOL",
                confidence=a_score / 4,
                allow_trades=True,
                param_overrides=self.config['overrides']['TRENDING_HIGH_VOL'],
                feature_snapshot=features,
                reasoning=f"Strong Trend & Vol (Score {a_score}/4)"
            )

        # REGIME B: TRENDING LOW VOL
        # ADX_5m >= 20 AND Choppiness < 50 AND Hurst > 0.52 AND RV_ratio <= 1.3
        b_score = 0
        if adx >= adx_weak: b_score += 1
        if chop < 50: b_score += 1
        if hurst > 0.52: b_score += 1
        if rv_ratio <= rv_high: b_score += 1
        
        if b_score >= 3:
            return RegimeDecision(
                regime="TRENDING_LOW_VOL",
                confidence=b_score / 4,
                allow_trades=True,
                param_overrides=self.config['overrides']['TRENDING_LOW_VOL'],
                feature_snapshot=features,
                reasoning=f"Steady Trend (Score {b_score}/4)"
            )

        # REGIME C: MEAN REVERTING
        # ADX_5m < 20 AND Choppiness between 38.2–61.8 AND Hurst < 0.48 AND range > 0.8×ATR
        c_score = 0
        if adx < adx_weak: c_score += 1
        if chop_trend <= chop <= chop_max: c_score += 1
        if hurst < hurst_revert: c_score += 1
        if range_ratio > 0.8: c_score += 1
        
        if c_score >= 3:
            return RegimeDecision(
                regime="MEAN_REVERTING",
                confidence=c_score / 4,
                allow_trades=True,
                param_overrides=self.config['overrides']['MEAN_REVERTING'],
                feature_snapshot=features,
                reasoning=f"Mean Reversion Zone (Score {c_score}/4)"
            )

        # FALLBACK: Safe default
        return RegimeDecision(
            regime="CHOPPY_UNTRADEABLE",
            confidence=0.5,
            allow_trades=False,
            param_overrides=self.config['overrides']['CHOPPY_UNTRADEABLE'],
            feature_snapshot=features,
            reasoning="Fallback: Mixed signals / Indecision"
        )
