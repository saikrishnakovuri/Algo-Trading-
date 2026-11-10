"""
Strategy: Spinning Top Candlestick Pattern
Category: candlestick
Source: Candlestickpatterns/Spinning Top Candlestick Pattern.md

Description:
  A single-candle neutral pattern signaling indecision.
  - Small real body.
  - Both upper and lower wicks are visible and relatively balanced.

Logic:
  - Body size <= 30% of total candle range.
  - Upper wick and Lower wick both > 0.5x Body size.
  - Wick ratio (Upper/Lower) between 0.5 and 2.0 for symmetry.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class SpinningTop(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Spinning Top"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 20
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        c = df.iloc[-1]
        
        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        
        if total_range == 0:
            return []
            
        upper_wick = c['high'] - max(c['open'], c['close'])
        lower_wick = min(c['open'], c['close']) - c['low']
        
        # 1. Small body relative to range
        is_small_body = body_size <= (total_range * 0.3)
        
        # 2. Both wicks visible and significant
        # If body is 0 (Doji), any wick is > 0.5*body. Use a small constant if body is tiny.
        safe_body = max(body_size, total_range * 0.05)
        wicks_visible = (upper_wick > safe_body * 0.5) and (lower_wick > safe_body * 0.5)
        
        # 3. Relatively balanced wicks (Symmetry)
        is_balanced = 0.5 <= (upper_wick / lower_wick) <= 2.0 if lower_wick > 0 else False
        
        if not (is_small_body and wicks_visible and is_balanced):
            return []
            
        # Context: After a move
        avg_range = (df['high'] - df['low']).tail(10).mean()
        after_move = total_range > avg_range * 0.8 # Not just a tiny dot
        
        if not after_move:
            return []
            
        bias = MarketBias.NEUTRAL
        if c['close'] > c['open']: bias = MarketBias.NEUTRAL # Green Spinning Top
        
        signals = [Signal(
            signal_type=SignalType.HOLD,
            strategy_name=self.name,
            confidence=0.5,
            timeframe=timeframe,
            market_bias=bias,
            reasoning=f"Spinning Top detected. Body: {body_size/total_range*100:.1f}% of range. Symmetrical wicks indicate equilibrium."
        )]
        
        return signals
