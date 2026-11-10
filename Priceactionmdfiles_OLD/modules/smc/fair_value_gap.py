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
        """
        Incremental update: checks for new FVGs and updates fill status.
        """
        if len(df) < 3: return self.fvgs
        
        # SPEED OPTIMIZATION: Only analyze the recent 100 bars for new formations
        lookback = 100
        start_idx = max(0, len(df) - lookback)

        # 1. Update existing FVGs
        self._update_lifecycle(df)
        
        # 2. Check for NEW FVG in the lookback window
        for i in range(start_idx + 2, len(df)):
            self._detect_new_fvg_at_idx(df, i, atr)
        
        # 3. Cleanup: drop FILLED FVGs older than retention limit
        i = len(df) - 1
        valid_fvgs = []
        for f in self.fvgs:
            try:
                loc = df.index.get_loc(f.created_at)
                if f.status != "FILLED" or (i - loc) < self.history_retention:
                    valid_fvgs.append(f)
            except (KeyError, ValueError):
                continue
        self.fvgs = valid_fvgs
        
        return self.fvgs

    def reset(self):
        """Reset detector state for a new symbol/session."""
        self.fvgs = []

    def _detect_new_fvg_at_idx(self, df: pd.DataFrame, i: int, atr: float):
        if i < 2: return
        
        c1, c2, c3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
        
        # Bullish FVG: c1.high < c3.low
        if c1['high'] < c3['low']:
            gap_size = c3['low'] - c1['high']
            if gap_size >= self.config.get('min_gap_atr', 0.25) * atr:
                new_fvg = FairValueGap(
                    fvg_high=float(c3['low']),
                    fvg_low=float(c1['high']),
                    created_at=df.index[i-1], # Center candle index
                    timeframe=self.tf,
                    direction="BULL",
                    gap_atr=float(gap_size / atr),
                    status="OPEN",
                    fill_pct=0.0,
                    strength=0.0
                )
                new_fvg.strength = self._calculate_strength(new_fvg)
                if not any(f.created_at == new_fvg.created_at for f in self.fvgs):
                    self.fvgs.append(new_fvg)
                    
        # Bearish FVG: c1.low > c3.high
        elif c1['low'] > c3['high']:
            gap_size = c1['low'] - c3['high']
            if gap_size >= self.config.get('min_gap_atr', 0.25) * atr:
                new_fvg = FairValueGap(
                    fvg_high=float(c1['low']),
                    fvg_low=float(c3['high']),
                    created_at=df.index[i-1],
                    timeframe=self.tf,
                    direction="BEAR",
                    gap_atr=float(gap_size / atr),
                    status="OPEN",
                    fill_pct=0.0,
                    strength=0.0
                )
                new_fvg.strength = self._calculate_strength(new_fvg)
                if not any(f.created_at == new_fvg.created_at for f in self.fvgs):
                    self.fvgs.append(new_fvg)

    def _detect_new_fvg(self, df: pd.DataFrame, atr: float):
        """Original signature for backward compatibility if needed, though update is primary."""
        self._detect_new_fvg_at_idx(df, len(df)-1, atr)

    def _update_lifecycle(self, df: pd.DataFrame):
        latest_high = df['high'].iloc[-1]
        latest_low = df['low'].iloc[-1]
        
        for f in self.fvgs:
            if f.status == "FILLED": continue
            
            gap_full_size = f.fvg_high - f.fvg_low
            
            if f.direction == "BULL":
                # Bullish gap (c1.high ... c3.low). Fill comes from above.
                if latest_low < f.fvg_high:
                    f.status = "PARTIALLY_FILLED"
                    current_fill = (f.fvg_high - latest_low) / gap_full_size
                    f.fill_pct = max(f.fill_pct, min(1.0, current_fill))
                    
                    if latest_low <= f.fvg_low:
                        f.status = "FILLED"
                        f.fill_pct = 1.0
            else:
                # Bearish gap (c3.high ... c1.low). Fill comes from below.
                if latest_high > f.fvg_low:
                    f.status = "PARTIALLY_FILLED"
                    current_fill = (latest_high - f.fvg_low) / gap_full_size
                    f.fill_pct = max(f.fill_pct, min(1.0, current_fill))
                    
                    if latest_high >= f.fvg_high:
                        f.status = "FILLED"
                        f.fill_pct = 1.0
            
            f.strength = self._calculate_strength(f)

    def _calculate_strength(self, fvg: FairValueGap) -> float:
        gap_comp = 0.5 * (fvg.gap_atr / 1.0)
        fill_comp = 0.3 * (1.0 - fvg.fill_pct)
        tf_comp = 0.2 * (0.5 if fvg.timeframe == "5m" else 0.3)
        
        return float(min(1.0, gap_comp + fill_comp + tf_comp))
