import pandas as pd
import numpy as np
from typing import Dict, List

class RelativeStrengthRanker:
    """
    Phase 28: Calculates Relative Strength (RS) to identify market leaders.
    """
    def __init__(self, window: int = 14):
        self.window = window

    def calculate_rs(self, stock_df: pd.DataFrame, index_df: pd.DataFrame) -> float:
        """
        Calculates RS Score: (Stock % Return) - (Index % Return) over window.
        """
        if len(stock_df) < self.window or len(index_df) < self.window:
            return 0.0
            
        stock_ret = (stock_df['close'].iloc[-1] / stock_df['close'].iloc[-self.window]) - 1
        index_ret = (index_df['close'].iloc[-1] / index_df['close'].iloc[-self.window]) - 1
        
        return (stock_ret - index_ret) * 100

    def rank_universe(self, universe_data: Dict[str, pd.DataFrame], index_symbol: str = "NIFTY") -> List[Dict]:
        index_df = universe_data.get(index_symbol)
        if index_df is None: return []
        
        rankings = []
        for sym, df in universe_data.items():
            if sym == index_symbol: continue
            rs_score = self.calculate_rs(df, index_df)
            rankings.append({"symbol": sym, "rs_score": round(rs_score, 3)})
            
        return sorted(rankings, key=lambda x: x['rs_score'], reverse=True)
