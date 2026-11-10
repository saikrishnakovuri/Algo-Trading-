"""
Strategy: Lower High & Lower Low (LH LL)
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Lower High & Lower Low.md

Description:
  LH & LL represent Bearish market structure.
  - Lower High (LH): Rally high below previous high.
  - Lower Low (LL): New low below previous low.

Logic:
  - Bearish Trend: LL -> LH -> LL -> LH
  - Entry: Rally to LH or Breakdown of LL.
  - Stop Loss: Above the recent LH.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class LowerHighLowerLow(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Lower High & Lower Low"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
    @property
    def required_candles(self) -> int:
        return 100
    
    def _find_swings(self, df: pd.DataFrame, window: int = 2) -> Dict[str, List[int]]:
        highs = df['high'].values
        lows = df['low'].values
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            if all(highs[i] > highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                swing_highs.append(i)
            if all(lows[i] < lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                swing_lows.append(i)
                
        return {"highs": swing_highs, "lows": swing_lows}

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
        
        swings = self._find_swings(df)
        high_indices = swings['highs']
        low_indices = swings['lows']
        
        if len(high_indices) < 2 or len(low_indices) < 2:
            return []
            
        # Get latest two swing points
        last_h = df['high'].iloc[high_indices[-1]]
        prev_h = df['high'].iloc[high_indices[-2]]
        last_l = df['low'].iloc[low_indices[-1]]
        prev_l = df['low'].iloc[low_indices[-2]]
        
        current_price = df['close'].iloc[-1]
        
        # Bearish Structure: LL + LH
        is_ll = last_l < prev_l
        is_lh = last_h < prev_h
        
        if not (is_ll and is_lh):
            return []
            
        signals = []
        
        # Check for LL breakdown (BOS)
        if current_price < last_l:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.75,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_h,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish LH LL structure confirmed. Current price broke LL ({last_l})."
            ))
        # Check if we are near LH (Rally entry)
        elif current_price < last_h and current_price > (last_h - (last_h - last_l) * 0.382):
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.85,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_h,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish LH LL structure confirmed. Price at LH rally zone ({current_price:.2f})."
            ))
        else:
            # General Bearish bias
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BEARISH,
                reasoning="Bearish LH LL structure identified, but price is not in an optimal entry zone."
            ))
            
        return signals
