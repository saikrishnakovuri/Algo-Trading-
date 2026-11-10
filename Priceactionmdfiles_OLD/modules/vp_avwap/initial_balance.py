import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from datetime import time, datetime

class InitialBalanceAnalyzer:
    """
    Analyzes the first 60 minutes of the session (Initial Balance).
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['ib']
        self.ib_duration = self.config.get('duration_minutes', 60)
        
    def compute_ib(self, df_1m: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes IB levels for the current session.
        """
        if df_1m.empty:
            return {}
            
        today = df_1m.index[-1].normalize()
        # IB Window: 09:15 to 10:15 IST
        # Data is UTC. 09:15 IST = 03:45 UTC. 10:15 IST = 04:45 UTC.
        # We'll use relative time from start of today's data.
        
        today_data = df_1m[df_1m.index >= today]
        if today_data.empty:
            return {}
            
        # First 60 bars of the session
        ib_data = today_data.iloc[:self.ib_duration]
        
        ibh = ib_data['high'].max()
        ibl = ib_data['low'].min()
        ib_range = ibh - ibl
        ib_mid = (ibh + ibl) / 2.0
        
        res = {
            'IBH': round(ibh, 2),
            'IBL': round(ibl, 2),
            'IB_mid': round(ib_mid, 2),
            'IB_range': round(ib_range, 2),
            'IBE_H1': round(ibh + 0.5 * ib_range, 2),
            'IBE_H2': round(ibh + 1.0 * ib_range, 2),
            'IBE_L1': round(ibl - 0.5 * ib_range, 2),
            'IBE_L2': round(ibl - 1.0 * ib_range, 2),
            'is_partial': len(ib_data) < self.ib_duration
        }
        
        # Day Type Classification (only if IB is complete and we have more data)
        res['day_type'] = self._classify_day_type(today_data, ibh, ibl, ib_range)
        
        return res

    def _classify_day_type(self, session_data: pd.DataFrame, ibh: float, ibl: float, ib_range: float) -> str:
        if len(session_data) <= self.ib_duration:
            return "UNDETERMINED"
            
        current_high = session_data['high'].max()
        current_low = session_data['low'].min()
        current_close = session_data['close'].iloc[-1]
        
        ext_up = current_high > ibh
        ext_dn = current_low < ibl
        
        if ext_up and ext_dn:
            return "Neutral Day"
        elif ext_up:
            if current_high > ibh + 1.0 * ib_range and current_close > ibh:
                return "Trend Day Up"
            else:
                return "Normal Variation"
        elif ext_dn:
            if current_low < ibl - 1.0 * ib_range and current_close < ibl:
                return "Trend Day Down"
            else:
                return "Normal Variation"
        else:
            return "Normal Day"
