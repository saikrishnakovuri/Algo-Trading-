import pandas as pd
import numpy as np
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from modules.vp_avwap.session_profile import SessionVolumeProfile

import joblib

class CompositeVolumeProfile:
    """
    Multi-day volume profile for structural context.
    """
    
    def __init__(self, config: Dict[str, Any], cache_dir: str = "data/composites/"):
        self.config = config
        self.vp_engine = SessionVolumeProfile(config)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def compute_composite(self, df_1m: pd.DataFrame, atr_5m: float, 
                          window_days: int, symbol: str) -> Dict[str, Any]:
        """
        Aggregates volume over window_days and extracts levels.
        """
        if df_1m.empty:
            return {}
            
        # Get unique trading days
        days = df_1m.index.normalize().unique()
        target_days = days[-window_days:]
        
        composite_df = df_1m[df_1m.index.normalize().isin(target_days)]
        
        # We can reuse SessionVolumeProfile.compute but with a wider data set
        # We adjust HVN/LVN count for composite
        temp_config = self.config.copy()
        temp_config['vp']['hvn_lvn_top_n'] = 5
        
        vp_composite = SessionVolumeProfile(temp_config)
        levels = vp_composite.compute(composite_df, atr_5m=atr_5m)
        
        # Add metadata
        levels['window_days'] = window_days
        levels['days_included'] = len(target_days)
        levels['last_date'] = str(target_days[-1].date())
        
        return levels

    def save_to_cache(self, symbol: str, levels: Dict[str, Any], window_days: int):
        file_path = self.cache_dir / f"{symbol}_{window_days}d.joblib"
        joblib.dump(levels, file_path)

    def load_from_cache(self, symbol: str, window_days: int) -> Optional[Dict[str, Any]]:
        file_path = self.cache_dir / f"{symbol}_{window_days}d.joblib"
        if not file_path.exists():
            return None
        return joblib.load(file_path)
