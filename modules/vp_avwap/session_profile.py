import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from numba import njit
from datetime import datetime

@njit
def distribute_volume_numba(lows, highs, closes, volumes, bin_edges, bin_volumes):
    """
    Numba-optimized volume distribution across bins.
    70% Close, 20% Mid, 10% Spread.
    """
    n_bars = len(lows)
    n_bins = len(bin_volumes)
    
    for i in range(n_bars):
        l, h, c, v = lows[i], highs[i], closes[i], volumes[i]
        
        # 70% to Close bin
        close_idx = np.searchsorted(bin_edges, c) - 1
        if 0 <= close_idx < n_bins:
            bin_volumes[close_idx] += v * 0.7
            
        # 20% to Mid bin
        mid = (h + l) / 2.0
        mid_idx = np.searchsorted(bin_edges, mid) - 1
        if 0 <= mid_idx < n_bins:
            bin_volumes[mid_idx] += v * 0.2
            
        # 10% Spread across range [l, h]
        start_idx = np.searchsorted(bin_edges, l) - 1
        end_idx = np.searchsorted(bin_edges, h) - 1
        
        start_idx = max(0, start_idx)
        end_idx = min(n_bins - 1, end_idx)
        
        n_spread_bins = end_idx - start_idx + 1
        if n_spread_bins > 0:
            v_spread_per_bin = (v * 0.1) / n_spread_bins
            for j in range(start_idx, end_idx + 1):
                bin_volumes[j] += v_spread_per_bin

class SessionVolumeProfile:
    """
    Computes intraday volume-at-price for the current session.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['vp']
        self.value_area_pct = self.config.get('value_area_pct', 70) / 100.0
        
    def compute(self, df_1m: pd.DataFrame, atr_5m: float, tick_size: float = 0.05) -> Dict[str, Any]:
        if df_1m.empty:
            return {}
            
        # 1. Determine Bin Size
        # bin_size = max(0.05 * ATR_5m, tick_size * 2)
        bin_size = max(self.config.get('bin_size_atr_multiplier', 0.05) * atr_5m, tick_size * 2)
        
        min_p = df_1m['low'].min()
        max_p = df_1m['high'].max()
        
        # Create bins
        bin_edges = np.arange(min_p - bin_size, max_p + 2*bin_size, bin_size)
        bin_volumes = np.zeros(len(bin_edges) - 1)
        
        # 2. Distribute Volume (Numba Optimized)
        distribute_volume_numba(
            df_1m['low'].values, 
            df_1m['high'].values, 
            df_1m['close'].values, 
            df_1m['volume'].values, 
            bin_edges, 
            bin_volumes
        )
        
        # 3. Extract POC, VAH, VAL
        poc_idx = np.argmax(bin_volumes)
        poc = bin_edges[poc_idx] + bin_size / 2.0
        
        total_vol = np.sum(bin_volumes)
        va_vol_target = total_vol * self.value_area_pct
        
        # Value Area Calculation (Standard: expand from POC)
        upper_idx = poc_idx
        lower_idx = poc_idx
        current_va_vol = bin_volumes[poc_idx]
        
        while current_va_vol < va_vol_target:
            # Check both sides for next available volume
            up_vol, up_steps = 0.0, 0
            for k in range(upper_idx + 1, len(bin_volumes)):
                up_steps += 1
                if bin_volumes[k] > 0:
                    up_vol = bin_volumes[k]
                    break
            
            dn_vol, dn_steps = 0.0, 0
            for k in range(lower_idx - 1, -1, -1):
                dn_steps += 1
                if bin_volumes[k] > 0:
                    dn_vol = bin_volumes[k]
                    break
            
            if up_vol == 0 and dn_vol == 0: break
            
            # Standard TPO/Volume Profile rule: add the side with more volume.
            # If equal, add both or pick one. Here we pick larger or closer.
            if up_vol > dn_vol:
                current_va_vol += up_vol
                upper_idx += up_steps
            elif dn_vol > up_vol:
                current_va_vol += dn_vol
                lower_idx -= dn_steps
            else:
                # Equal volume: pick the closer one
                if up_steps <= dn_steps:
                    current_va_vol += up_vol
                    upper_idx += up_steps
                else:
                    current_va_vol += dn_vol
                    lower_idx -= dn_steps
                
        vah = bin_edges[upper_idx + 1]
        val = bin_edges[lower_idx]
        
        # 4. HVNs and LVNs
        # HVNs: Local maxima
        hvns = []
        for i in range(1, len(bin_volumes) - 1):
            if bin_volumes[i] > bin_volumes[i-1] and bin_volumes[i] > bin_volumes[i+1]:
                price = bin_edges[i] + bin_size / 2.0
                strength = bin_volumes[i] / bin_volumes[poc_idx]
                hvns.append({'price': price, 'strength': strength})
        
        hvns = sorted(hvns, key=lambda x: x['strength'], reverse=True)[:self.config.get('hvn_lvn_top_n', 3)]
        
        # LVNs: Local minima between HVNs (simplified: overall minima)
        lvns = []
        if len(hvns) >= 2:
            for i in range(len(hvns) - 1):
                p1, p2 = sorted([hvns[i]['price'], hvns[i+1]['price']])
                mask = (bin_edges[:-1] >= p1) & (bin_edges[:-1] <= p2)
                if np.any(mask):
                    sub_vols = bin_volumes[mask]
                    min_idx_in_mask = np.argmin(sub_vols)
                    lvn_price = bin_edges[:-1][mask][min_idx_in_mask] + bin_size/2.0
                    lvns.append({'price': lvn_price, 'strength': 1.0 - (sub_vols[min_idx_in_mask] / bin_volumes[poc_idx])})

        # 5. dPOC History
        # In a real system, we'd compute this bar-by-bar.
        # For the skeleton, we return the current POC.
        
        return {
            'POC': round(poc, 2),
            'VAH': round(vah, 2),
            'VAL': round(val, 2),
            'HVNs': hvns,
            'LVNs': lvns,
            'bin_size': bin_size,
            'total_volume': total_vol
        }
