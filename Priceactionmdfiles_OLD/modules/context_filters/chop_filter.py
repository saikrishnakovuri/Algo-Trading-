import numpy as np
import pandas as pd
from typing import Dict, Any, List
from modules.context_filters.schemas import ChopVerdict

class ChopFilter:
    """
    Multi-dimensional, regime-aware chop filter.
    Uses 4 independent metrics: RCR, BBR, ZZD, VD.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['chop']
        self.weights = self.config['weights']
        
    def evaluate(self, df_5m: pd.DataFrame, atr_14_5m: float, regime: str) -> ChopVerdict:
        if len(df_5m) < 12:
            return ChopVerdict(verdict="ALLOW", chop_score=0.0, metrics={}, regime_adjusted_threshold=0.6, reasoning="Insufficient bars")
            
        sub = df_5m.iloc[-12:]
        
        # M1: Range Compression Ratio (RCR)
        # RCR = (max(H, 12) - min(L, 12)) / ATR_14_5m
        rcr = (sub['high'].max() - sub['low'].min()) / atr_14_5m if atr_14_5m > 0 else 1.0
        is_rcr_choppy = rcr < self.config['rcr_threshold']
        
        # M2: Bar Body Ratio (BBR)
        # BBR = mean( |close - open| / (high - low) )
        bodies = (sub['close'] - sub['open']).abs()
        ranges = sub['high'] - sub['low']
        # Avoid division by zero
        bbr_series = bodies / ranges.replace(0, 0.0001)
        bbr = bbr_series.mean()
        is_bbr_choppy = bbr < self.config['bbr_threshold']
        
        # M3: Zigzag Density (ZZD)
        # Count direction flips (close direction change)
        close_diff = sub['close'].diff().dropna()
        # Sign of difference: 1 for up, -1 for down
        signs = np.sign(close_diff.replace(0, method='ffill'))
        # Direction flip if sign[i] != sign[i-1]
        flips = (signs != signs.shift(1)).dropna().sum()
        zzd = int(flips)
        is_zzd_choppy = zzd >= self.config['zzd_threshold']
        
        # M4: Volume Dispersion (VD)
        # VD = std volume / mean volume
        vd = sub['volume'].std() / sub['volume'].mean() if sub['volume'].mean() > 0 else 0
        is_vd_choppy = vd < self.config['vd_threshold']
        
        # Composite Score
        score = (self.weights['rcr'] * is_rcr_choppy +
                 self.weights['bbr'] * is_bbr_choppy +
                 self.weights['zzd'] * is_zzd_choppy +
                 self.weights['vd'] * is_vd_choppy)
        
        # Regime-aware threshold
        veto_threshold = self.config['veto_score']
        overrides = self.config.get('regime_overrides', {})
        if regime in overrides:
            veto_threshold = overrides[regime]['veto_score']
            
        metrics = {"RCR": round(rcr, 2), "BBR": round(bbr, 2), "ZZD": zzd, "VD": round(vd, 2)}
        
        if score >= veto_threshold:
            verdict = "VETO"
        elif score >= self.config['warn_score']:
            verdict = "WARN"
        else:
            verdict = "ALLOW"
            
        reasoning = []
        if is_rcr_choppy: reasoning.append(f"RCR compressed ({rcr:.2f})")
        if is_bbr_choppy: reasoning.append(f"BBR wicky ({bbr:.2f})")
        if is_zzd_choppy: reasoning.append(f"ZZD oscillating ({zzd})")
        if is_vd_choppy: reasoning.append(f"VD flat volume ({vd:.2f})")
        
        return ChopVerdict(
            verdict=verdict,
            chop_score=round(score, 2),
            metrics=metrics,
            regime_adjusted_threshold=veto_threshold,
            reasoning=" | ".join(reasoning) if reasoning else "Market trending/active"
        )
