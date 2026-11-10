"""
Strategy: Higher High & Higher Low (HH HL)
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Higher High & Higher Low.md

Description:
  HH & HL represent Bullish market structure.
  - Higher High (HH): New high above previous high.
  - Higher Low (HL): Pullback low above previous low.

Logic:
  - Bullish Trend: HH -> HL -> HH -> HL
  - Entry: Pullback to HL or Breakout of HH.
  - Stop Loss: Below the recent HL.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class HigherHighHigherLow(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Higher High & Higher Low"
    
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
        
        # Bullish Structure: HH + HL
        is_hh = last_h > prev_h
        is_hl = last_l > prev_l
        
        if not (is_hh and is_hl):
            return []
            
        signals = []
        
        # Check for HH breakout (BOS)
        if current_price > last_h:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.75,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_l,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish HH HL structure confirmed. Current price broke HH ({last_h})."
            ))
        # Check if we are near HL (Pullback entry)
        elif current_price > last_l and current_price < (last_l + (last_h - last_l) * 0.382):
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.85,  # Pullback entries have higher RR/confidence
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_l,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish HH HL structure confirmed. Price at HL pullback zone ({current_price:.2f})."
            ))
        else:
            # General Bullish bias
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BULLISH,
                reasoning="Bullish HH HL structure identified, but price is not in an optimal entry zone."
            ))
            
        return signals
