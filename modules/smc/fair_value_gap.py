import numpy as np
import pandas as pd
from datetime import datetime
try:
    from typing import List, Dict, Any, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import List, Dict, Any, Optional, Union
    Literal = Any
from modules.smc.schemas import FairValueGap

class FairValueGapDetector:
    """
    Deterministic Fair Value Gap (FVG) detector with lifecycle tracking.
    """
    
    def __init__(self, config: Dict[str, Any], timeframe: Literal["5m", "1m"]):
        self.config = config['smc']['fvg']
        self.tf = timeframe
        self.fvgs: List[FairValueGap] = []
        self.history_retention = self.config.get('history_retention_bars', 30)
        
    def update(self, df: pd.DataFrame, atr: float) -> List[FairValueGap]:
        if len(df) < 3: return self.fvgs
        
        # SPEED OPTIMIZATION
        lookback = 50
        start_idx = max(2, len(df) - lookback)

        highs = df['high'].values
        lows = df['low'].values
        times = df.index

        # 1. Update existing FVGs
        self._update_lifecycle_np(highs, lows)
        
        # 2. Check for NEW FVG
        for i in range(start_idx, len(df)):
            self._detect_new_fvg_np(highs, lows, times, i, atr)
        
        # 3. Cleanup
        curr_len = len(df)
        self.fvgs = [f for f in self.fvgs if f.status != "FILLED"]
        if len(self.fvgs) > 50: self.fvgs = self.fvgs[-50:]
        
        return self.fvgs

    def reset(self):
        self.fvgs = []

    def _detect_new_fvg_np(self, highs, lows, times, i, atr):
        # i is current, check i-2, i-1, i
        h1, h3 = highs[i-2], highs[i]
        l1, l3 = lows[i-2], lows[i]
        
        if h1 < l3: # Bullish
            gap = l3 - h1
            if gap >= self.config.get('min_gap_atr', 0.25) * atr:
                new_fvg = FairValueGap(
                    fvg_high=float(l3), fvg_low=float(h1), created_at=times[i-1],
                    timeframe=self.tf, direction="BULL", gap_atr=float(gap / atr),
                    status="OPEN", fill_pct=0.0, strength=0.0
                )
                new_fvg.strength = self._calculate_strength(new_fvg)
                if not any(f.created_at == new_fvg.created_at for f in self.fvgs):
                    self.fvgs.append(new_fvg)
        elif l1 > h3: # Bearish
            gap = l1 - h3
            if gap >= self.config.get('min_gap_atr', 0.25) * atr:
                new_fvg = FairValueGap(
                    fvg_high=float(l1), fvg_low=float(h3), created_at=times[i-1],
                    timeframe=self.tf, direction="BEAR", gap_atr=float(gap / atr),
                    status="OPEN", fill_pct=0.0, strength=0.0
                )
                new_fvg.strength = self._calculate_strength(new_fvg)
                if not any(f.created_at == new_fvg.created_at for f in self.fvgs):
                    self.fvgs.append(new_fvg)

    def _update_lifecycle_np(self, highs, lows):
        lh, ll = highs[-1], lows[-1]
        for f in self.fvgs:
            if f.status == "FILLED": continue
            size = f.fvg_high - f.fvg_low
            if f.direction == "BULL":
                if ll < f.fvg_high:
                    f.status = "PARTIALLY_FILLED"
                    f.fill_pct = max(f.fill_pct, min(1.0, (f.fvg_high - ll) / size))
                    if ll <= f.fvg_low: f.status, f.fill_pct = "FILLED", 1.0
            else:
                if lh > f.fvg_low:
                    f.status = "PARTIALLY_FILLED"
                    f.fill_pct = max(f.fill_pct, min(1.0, (lh - f.fvg_low) / size))
                    if lh >= f.fvg_high: f.status, f.fill_pct = "FILLED", 1.0
            f.strength = self._calculate_strength(f)

    def _calculate_strength(self, fvg: FairValueGap) -> float:
        g = 0.5 * (fvg.gap_atr / 1.0)
        f = 0.3 * (1.0 - fvg.fill_pct)
        tf = 0.2 * (0.5 if fvg.timeframe == "5m" else 0.3)
        return float(min(1.0, g + f + tf))
