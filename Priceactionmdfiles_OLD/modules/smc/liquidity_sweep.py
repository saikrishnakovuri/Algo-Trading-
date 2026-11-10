import numpy as np
import pandas as pd
from datetime import datetime, time
try:
    from typing import List, Dict, Any, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import List, Dict, Any, Optional, Union
    Literal = Any
from modules.smc.schemas import LiquiditySweep

class LiquiditySweepDetector:
    """
    Identifies liquidity pools and detects sweeps with reversal confirmation.
    """
    
    def __init__(self, config: Dict[str, Any], timeframe: Literal["5m", "1m"]):
        self.config = config['smc']['liquidity_sweep']
        self.tf = timeframe
        self.sweeps: List[LiquiditySweep] = []
        self.pools: List[Dict[str, Any]] = [] # list of {level, type, tier}
        
    def update(self, df: pd.DataFrame, atr: float, 
               prior_ohlc: Dict[str, float], 
               preopen_range: Dict[str, float]) -> List[LiquiditySweep]:
        """
        Incremental update: identifies pools and checks for sweeps.
        """
        if len(df) < 5: return self.sweeps
        
        # 1. Update/Refresh Liquidity Pools
        self._refresh_pools(df, prior_ohlc, preopen_range, atr)
        
        # 2. Check for sweeps
        self._detect_sweeps(df, atr)
        
        # 3. Cleanup: expire old sweeps
        i = len(df) - 1
        self.sweeps = [s for s in self.sweeps if (i - s.sweep_candle_idx) < self.config.get('active_lifetime_bars', 20)]
        
        return self.sweeps

    def _refresh_pools(self, df: pd.DataFrame, prior_ohlc: Dict[str, float], 
                       preopen_range: Dict[str, float], atr: float):
        self.pools = []
        
        # Tier 1: PDH / PDL
        if prior_ohlc:
            if 'high' in prior_ohlc: self.pools.append({'level': prior_ohlc['high'], 'type': 'PDH', 'tier': 1})
            if 'low' in prior_ohlc: self.pools.append({'level': prior_ohlc['low'], 'type': 'PDL', 'tier': 1})
            
        # Tier 2: Session H/L
        today = df.index[-1].normalize()
        today_data = df[df.index >= today]
        if not today_data.empty:
            sh = today_data['high'].max()
            sl = today_data['low'].min()
            self.pools.append({'level': sh, 'type': 'SH', 'tier': 2})
            self.pools.append({'level': sl, 'type': 'SL', 'tier': 2})
            
        # Tier 3: EQH / EQL (using swing detection)
        lookback = self.config.get('lookback_bars', 20)
        tol = self.config.get('equal_level_tolerance_pct', 0.1)
        eqh, eql = self._find_swing_points(df, lookback=lookback, pivot_strength=2, tolerance_pct=tol)
        
        for pool in eqh:
            self.pools.append({'level': pool['level'], 'type': 'EQH', 'tier': 3, 'touches': pool['touches']})
        for pool in eql:
            self.pools.append({'level': pool['level'], 'type': 'EQL', 'tier': 3, 'touches': pool['touches']})
            
        # Tier 4: Preopen Range
        if preopen_range:
            if 'high' in preopen_range: self.pools.append({'level': preopen_range['high'], 'type': 'PREOPEN_H', 'tier': 4})
            if 'low' in preopen_range: self.pools.append({'level': preopen_range['low'], 'type': 'PREOPEN_L', 'tier': 4})

        levels_above = [p for p in self.pools if "H" in p['type'] or p['type'] == "SH"]
        levels_below = [p for p in self.pools if "L" in p['type'] or p['type'] == "SL"]
        
        return self.pools

    def _find_swing_points(self, df: pd.DataFrame, lookback: int = 20, pivot_strength: int = 2,
                           tolerance_pct: float = 0.1):
        """
        Identify intraday swing highs/lows (EQH/EQL) within last `lookback` bars.
        A pivot = bar whose high is strictly greater than `pivot_strength` bars on each side.
        Multiple pivots within `tolerance_pct` of each other cluster as one equal-level pool.
        """
        if len(df) < lookback + pivot_strength * 2:
            return [], []

        recent = df.iloc[-lookback - pivot_strength:].copy()
        highs = recent['high'].values
        lows = recent['low'].values
        n = len(recent)

        pivot_highs = []
        pivot_lows = []
        for i in range(pivot_strength, n - pivot_strength):
            window_high = highs[i - pivot_strength:i + pivot_strength + 1]
            window_low = lows[i - pivot_strength:i + pivot_strength + 1]
            if highs[i] == window_high.max() and (window_high == highs[i]).sum() == 1:
                pivot_highs.append(highs[i])
            if lows[i] == window_low.min() and (window_low == lows[i]).sum() == 1:
                pivot_lows.append(lows[i])

        def cluster(levels):
            if not levels: return []
            levels_sorted = sorted(levels)
            clusters = []
            current = [levels_sorted[0]]
            for lvl in levels_sorted[1:]:
                ref = sum(current) / len(current)
                if abs(lvl - ref) / ref * 100 <= tolerance_pct:
                    current.append(lvl)
                else:
                    clusters.append({'level': sum(current) / len(current), 'touches': len(current)})
                    current = [lvl]
            clusters.append({'level': sum(current) / len(current), 'touches': len(current)})
            return clusters

        return cluster(pivot_highs), cluster(pivot_lows)

    def _detect_sweeps(self, df: pd.DataFrame, atr: float):
        i = len(df) - 1
        if i < 4: return
        
        # Optimization: only check last 3 candles for the 'sweep' event
        for lookback in range(3):
            idx = i - lookback
            candle = df.iloc[idx]
            
            for pool in self.pools:
                level = pool['level']
                p_type = pool['type']
                
                penetration = self.config.get('penetration_min_atr', 0.1) * atr
                
                # Check for High Sweep (SH/PDH/EQH/PREOPEN_H)
                if "H" in p_type or p_type == "SH":
                    if candle['high'] > level + penetration:
                        # Sweep detected! Now check for reversal within window
                        # For 1m: within next 3 candles price closes back inside
                        # For 5m: within next 1 candle
                        window = self.config.get('reversal_bars_1m', 3) if self.tf == "1m" else self.config.get('reversal_bars_5m', 1)
                        
                        found_reversal = False
                        rev_idx = None
                        for r in range(idx, min(len(df), idx + window + 1)):
                            if df.iloc[r]['close'] < level:
                                found_reversal = True
                                rev_idx = r
                                break
                        
                        if found_reversal:
                            # Volume check on sweep candle
                            vol_mean = df['volume'].rolling(20).mean().iloc[idx]
                            if candle['volume'] >= vol_mean * self.config.get('volume_ratio_min', 1.5):
                                self._add_sweep(candle['high'], level, idx, rev_idx, p_type, pool['tier'], df, atr)

                # Check for Low Sweep (SL/PDL/EQL/PREOPEN_L)
                elif "L" in p_type or p_type == "SL":
                    if candle['low'] < level - penetration:
                        window = self.config.get('reversal_bars_1m', 3) if self.tf == "1m" else self.config.get('reversal_bars_5m', 1)
                        found_reversal = False
                        rev_idx = None
                        for r in range(idx, min(len(df), idx + window + 1)):
                            if df.iloc[r]['close'] > level:
                                found_reversal = True
                                rev_idx = r
                                break
                                
                        if found_reversal:
                            vol_mean = df['volume'].rolling(20).mean().iloc[idx]
                            if candle['volume'] >= vol_mean * self.config.get('volume_ratio_min', 1.5):
                                self._add_sweep(candle['low'], level, idx, rev_idx, p_type, pool['tier'], df, atr)

    def _add_sweep(self, sweep_price, pool_level, s_idx, r_idx, p_type, tier, df, atr):
        # Avoid duplicates
        if any(s.sweep_candle_idx == s_idx and s.pool_type == p_type for s in self.sweeps):
            return
            
        new_sweep = LiquiditySweep(
            sweep_price=float(sweep_price),
            pool_level=float(pool_level),
            sweep_candle_idx=s_idx,
            reversal_candle_idx=r_idx,
            pool_type=p_type,
            tier=tier,
            timeframe=self.tf,
            volume_ratio=float(df.iloc[s_idx]['volume'] / df['volume'].rolling(20).mean().iloc[s_idx]),
            atr_penetration=float(abs(sweep_price - pool_level) / atr),
            status="ACTIVE"
        )
        self.sweeps.append(new_sweep)
