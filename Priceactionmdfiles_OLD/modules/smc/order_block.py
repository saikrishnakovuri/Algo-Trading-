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
        """
        Incremental update: checks for new OBs and updates mitigation status of existing ones.
        df: OHLCV data for the timeframe.
        """
        if len(df) < 5: return self.obs
        
        # SPEED OPTIMIZATION: Only analyze the recent 100 bars for new formations
        # This prevents the loop from getting slower as the backtest progresses
        lookback = 100
        start_idx = max(0, len(df) - lookback)
        
        # 1. Update mitigation for existing OBs
        self._update_lifecycle(df)
        
        # 2. Check for NEW OB formation in the lookback window
        for i in range(start_idx + 4, len(df)):
            self._detect_new_ob(df, i, atr)
        
        # 3. Cleanup: remove invalidated or extremely old OBs
        valid_obs = []
        for ob in self.obs:
            if ob.status == "INVALIDATED": continue
            try:
                bars_since = i - df.index.get_loc(ob.created_at)
                if bars_since < self.max_age:
                    valid_obs.append(ob)
            except (KeyError, ValueError):
                continue
        self.obs = valid_obs
        
        return self.obs

    def reset(self):
        """Reset detector state for a new symbol/session."""
        self.obs = []

    def _detect_new_ob(self, df: pd.DataFrame, current_idx: int, atr: float):
        idx = current_idx - 3
        cand_ob = df.iloc[idx]
        d1, d2, d3 = df.iloc[idx+1], df.iloc[idx+2], df.iloc[idx+3]
        
        is_bull_disp = (d1['close'] > d1['open']) and (d2['close'] > d2['open']) and (d3['close'] > d3['open'])
        is_bear_disp = (d1['close'] < d1['open']) and (d2['close'] < d2['open']) and (d3['close'] < d3['open'])
        
        if not (is_bull_disp or is_bear_disp): return

        total_range = abs(d3['close'] - d1['open'])
        if total_range < self.config.get('displacement_atr_min', 1.5) * atr: return
        
        if is_bull_disp:
            if d2['low'] < d1['low'] or d3['low'] < d2['low']: return
            if cand_ob['close'] >= cand_ob['open']: return 
            direction = "BULL"
        else:
            if d2['high'] > d1['high'] or d3['high'] > d2['high']: return
            if cand_ob['close'] <= cand_ob['open']: return 
            direction = "BEAR"
            
        vol_mean = df['volume'].rolling(20).mean().iloc[current_idx]
        disp_vol_avg = (d1['volume'] + d2['volume'] + d3['volume']) / 3.0
        if disp_vol_avg < vol_mean * self.config.get('volume_ratio_min', 1.3): return
        
        new_ob = OrderBlock(
            ob_high=float(cand_ob['high']),
            ob_low=float(cand_ob['low']),
            ob_open=float(cand_ob['open']),
            ob_close=float(cand_ob['close']),
            created_at=df.index[idx],
            timeframe=self.tf,
            direction=direction,
            displacement_atr=float(total_range / atr),
            status="UNMITIGATED",
            touches=0,
            strength=0.0 
        )
        new_ob.strength = self._calculate_strength(new_ob, 0)
        if not any(ob.created_at == new_ob.created_at for ob in self.obs):
            self.obs.append(new_ob)

    def _update_lifecycle(self, df: pd.DataFrame):
        latest_price = df['close'].iloc[-1]
        latest_low = df['low'].iloc[-1]
        latest_high = df['high'].iloc[-1]
        
        for ob in self.obs:
            if ob.status == "INVALIDATED": continue
            
            midpoint = (ob.ob_high + ob.ob_low) / 2.0
            
            if ob.direction == "BULL":
                if latest_low <= ob.ob_high:
                    if ob.status == "UNMITIGATED":
                        ob.status = "MITIGATED_PARTIAL"
                        ob.touches += 1
                    if latest_price < midpoint:
                        ob.status = "MITIGATED_FULL"
                    if latest_price < ob.ob_low:
                        ob.status = "INVALIDATED"
            else:
                if latest_high >= ob.ob_low:
                    if ob.status == "UNMITIGATED":
                        ob.status = "MITIGATED_PARTIAL"
                        ob.touches += 1
                    if latest_price > midpoint:
                        ob.status = "MITIGATED_FULL"
                    if latest_price > ob.ob_high:
                        ob.status = "INVALIDATED"

            try:
                bars_since = len(df) - 1 - df.index.get_loc(ob.created_at)
                ob.strength = self._calculate_strength(ob, bars_since)
            except (KeyError, ValueError):
                continue

    def _calculate_strength(self, ob: OrderBlock, bars_since: int) -> float:
        disp_comp = 0.4 * (ob.displacement_atr / 3.0)
        touch_comp = 0.3 * (1.0 / max(1, ob.touches))
        tf_comp = 0.3 * (0.5 if ob.timeframe == "5m" else 0.3)
        decay = 0.1 * np.exp(-bars_since / 80.0)
        
        return float(min(1.0, disp_comp + touch_comp + tf_comp + decay))
