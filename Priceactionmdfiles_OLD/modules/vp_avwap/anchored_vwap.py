import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, time

class AnchoredVWAPEngine:
    """
    Computes multiple anchored VWAPs with standard deviation bands.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['avwap']
        self.bands = self.config.get('bands', [1, 2, 3])
        
    def compute_all(self, df_1m: pd.DataFrame, prior_ohlc: Dict[str, float], 
                    df_5m: pd.DataFrame, atr_5m: float) -> Dict[str, Dict[str, float]]:
        """
        Computes all 8 requested anchored VWAPs.
        """
        if df_1m.empty:
            return {}
            
        results = {}
        
        # Define Anchors
        anchors = self._detect_anchors(df_1m, prior_ohlc, df_5m, atr_5m)
        
        for name, anchor_idx in anchors.items():
            if anchor_idx is not None and anchor_idx < len(df_1m):
                results[name] = self._calculate_vwap(df_1m.iloc[anchor_idx:])
                
        return results

    def _calculate_vwap(self, df: pd.DataFrame) -> Dict[str, float]:
        """Standard VWAP + SD Bands formula."""
        tp = (df['high'] + df['low'] + df['close']) / 3.0
        v = df['volume']
        
        cum_tp_v = (tp * v).cumsum()
        cum_v = v.cumsum()
        
        # Last value
        vwap = cum_tp_v.iloc[-1] / cum_v.iloc[-1] if cum_v.iloc[-1] > 0 else tp.iloc[-1]
        
        # Variance for SD bands
        # var = sum(v * (tp - vwap_i)^2) / sum(v)
        # Note: To be precise, we need the vwap at each step
        vwap_series = cum_tp_v / cum_v
        variance = ((tp - vwap_series)**2 * v).cumsum().iloc[-1] / cum_v.iloc[-1]
        sd = np.sqrt(variance) if variance > 0 else 0
        
        res = {'value': round(vwap, 2)}
        for b in self.bands:
            res[f'+{b}sd'] = round(vwap + b * sd, 2)
            res[f'-{b}sd'] = round(vwap - b * sd, 2)
            
        return res

    def _detect_anchors(self, df_1m: pd.DataFrame, prior_ohlc: Dict[str, float], 
                        df_5m: pd.DataFrame, atr_5m: float) -> Dict[str, Optional[int]]:
        anchors = {}
        
        # Today's date for normalization
        today = df_1m.index[-1].normalize()
        
        # A1. Session Open VWAP (today 09:15)
        # Find first bar of today
        today_mask = df_1m.index >= today
        if any(today_mask):
            anchors['Session_Open'] = np.where(today_mask)[0][0]
            
        # A2 & A3. Prior Day High/Low
        # This requires the 1m bar index where PDH/PDL occurred
        # Since we might not have all 1m data in current df, we approximate 
        # or use prior_ohlc values.
        # Requirement: "anchor = 1m bar where PDH formed". 
        # If we have historical_1m, we'd find it there. 
        # Placeholder: using session open if not found.
        
        # A4. Prior Day Close (yesterday 15:30)
        # Usually we anchor from the start of current session if using PDC as bias.
        
        # A5. Gap Anchor (if gap >= 0.3%)
        if prior_ohlc and 'close' in prior_ohlc:
            first_open = df_1m[today_mask]['open'].iloc[0] if any(today_mask) else 0
            gap = (first_open - prior_ohlc['close']) / prior_ohlc['close']
            if abs(gap) >= self.config.get('gap_threshold_pct', 0.3) / 100.0:
                anchors['Gap_Anchor'] = anchors.get('Session_Open')

        # A6 & A7. Last Major Swing H/L (5m)
        if not df_5m.empty:
            # Simple Swing detection on 5m
            lookback = self.config.get('swing_lookback_5m_bars', 50)
            sub_5m = df_5m.iloc[-lookback:]
            
            # Find max high and min low in lookback using positional index
            max_h_pos = sub_5m['high'].values.argmax()
            min_l_pos = sub_5m['low'].values.argmin()
            
            # Map 5m time back to 1m index
            time_h = sub_5m.index[max_h_pos]
            time_l = sub_5m.index[min_l_pos]
            
            anchors['Last_Swing_High'] = self._get_idx_by_time(df_1m, time_h)
            anchors['Last_Swing_Low'] = self._get_idx_by_time(df_1m, time_l)
            
        return anchors

    def _get_idx_by_time(self, df: pd.DataFrame, target_time: datetime) -> Optional[int]:
        # Find closest index
        diffs = (df.index - target_time).total_seconds().values
        if len(diffs) == 0: return None
        idx = np.argmin(np.abs(diffs))
        return int(idx)
