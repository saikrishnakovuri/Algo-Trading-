import numpy as np
import pandas as pd
from datetime import datetime
try:
    from typing import List, Dict, Any, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import List, Dict, Any, Optional, Union
    Literal = Any
from modules.smc.schemas import OrderBlock

class OrderBlockDetector:
    """
    Deterministic Order Block detector with lifecycle tracking.
    """
    
    def __init__(self, config: Dict[str, Any], timeframe: Literal["5m", "1m"]):
        self.config = config['smc']['order_block']
        self.tf = timeframe
        self.obs: List[OrderBlock] = []
        self.max_age = self.config.get(f'max_age_bars_{self.tf}', 200)
        
    def update(self, df: pd.DataFrame, atr: float) -> List[OrderBlock]:
        if len(df) < 5: return self.obs
        
        # Incremental logic: only check the NEW bars since last update
        # For simplicity in this optimization, we still use a small lookback
        lookback = 50 
        start_idx = max(0, len(df) - lookback)
        
        # Convert to numpy for SPEED
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        vols = df['volume'].values
        times = df.index
        
        # 1. Update mitigation for existing OBs
        self._update_lifecycle_np(closes, highs, lows, times)
        
        # 2. Check for NEW OB formation
        # Precalculate vol_mean if needed, but here we just use it locally
        vol_rolling_mean = df['volume'].rolling(20).mean().values
        
        for i in range(max(4, start_idx), len(df)):
            self._detect_new_ob_np(opens, highs, lows, closes, vols, times, vol_rolling_mean, i, atr)
        
        # 3. Cleanup
        curr_time = times[-1]
        self.obs = [ob for ob in self.obs if ob.status != "INVALIDATED"]
        # Limit by age (approximate)
        if len(self.obs) > 50: self.obs = self.obs[-50:]
        
        return self.obs

    def reset(self):
        self.obs = []

    def _detect_new_ob_np(self, opens, highs, lows, closes, vols, times, vol_means, current_idx, atr):
        idx = current_idx - 3
        # Displacement check (next 3 bars)
        d1_c, d1_o = closes[idx+1], opens[idx+1]
        d2_c, d2_o = closes[idx+2], opens[idx+2]
        d3_c, d3_o = closes[idx+3], opens[idx+3]
        
        is_bull_disp = (d1_c > d1_o) and (d2_c > d2_o) and (d3_c > d3_o)
        is_bear_disp = (d1_c < d1_o) and (d2_c < d2_o) and (d3_c < d3_o)
        
        if not (is_bull_disp or is_bear_disp): return

        total_range = abs(d3_c - d1_o)
        if total_range < self.config.get('displacement_atr_min', 1.5) * atr: return
        
        c_ob_c, c_ob_o = closes[idx], opens[idx]
        if is_bull_disp:
            if lows[idx+2] < lows[idx+1] or lows[idx+3] < lows[idx+2]: return
            if c_ob_c >= c_ob_o: return 
            direction = "BULL"
        else:
            if highs[idx+2] > highs[idx+1] or highs[idx+3] > highs[idx+2]: return
            if c_ob_c <= c_ob_o: return 
            direction = "BEAR"
            
        disp_vol_avg = (vols[idx+1] + vols[idx+2] + vols[idx+3]) / 3.0
        if disp_vol_avg < vol_means[current_idx] * self.config.get('volume_ratio_min', 1.3): return
        
        new_ob = OrderBlock(
            ob_high=float(highs[idx]), ob_low=float(lows[idx]),
            ob_open=float(opens[idx]), ob_close=float(closes[idx]),
            created_at=times[idx], timeframe=self.tf, direction=direction,
            displacement_atr=float(total_range / atr), status="UNMITIGATED",
            touches=0, strength=0.0 
        )
        new_ob.strength = self._calculate_strength(new_ob, 0)
        if not any(ob.created_at == new_ob.created_at for ob in self.obs):
            self.obs.append(new_ob)

    def _update_lifecycle_np(self, closes, highs, lows, times):
        lp, l_low, l_high = closes[-1], lows[-1], highs[-1]
        total_len = len(closes)
        for ob in self.obs:
            if ob.status == "INVALIDATED": continue
            mid = (ob.ob_high + ob.ob_low) / 2.0
            if ob.direction == "BULL":
                if l_low <= ob.ob_high:
                    if ob.status == "UNMITIGATED": ob.status = "MITIGATED_PARTIAL"; ob.touches += 1
                    if lp < mid: ob.status = "MITIGATED_FULL"
                    if lp < ob.ob_low: ob.status = "INVALIDATED"
            else:
                if l_high >= ob.ob_low:
                    if ob.status == "UNMITIGATED": ob.status = "MITIGATED_PARTIAL"; ob.touches += 1
                    if lp > mid: ob.status = "MITIGATED_FULL"
                    if lp > ob.ob_high: ob.status = "INVALIDATED"
            
            # Decay calculation
            # For speed, we just use a generic index-based decay if created_at is in index
            # This part is still a bit slow due to list search/index, but obs list is small
            ob.strength = self._calculate_strength(ob, 10) # Placeholder for decay

    def _calculate_strength(self, ob: OrderBlock, bars_since: int) -> float:
        d = 0.4 * (ob.displacement_atr / 3.0)
        t = 0.3 * (1.0 / max(1, ob.touches))
        tf = 0.3 * (0.5 if ob.timeframe == "5m" else 0.3)
        decay = 0.1 * np.exp(-bars_since / 80.0)
        return float(min(1.0, d + t + tf + decay))
