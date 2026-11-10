"""
Strategy: Break of Structure (BOS)
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Break of Structure (BOS).md

Description:
  BOS represents trend continuation confirmation.
  - Bullish BOS: Price breaks previous Higher High (HH).
  - Bearish BOS: Price breaks previous Lower Low (LL).

Logic:
  - Valid BOS requires "displacement" (strong movement, volume).
  - Confirms the intent of institutional traders to continue the trend.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BreakOfStructure(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Break of Structure (BOS)"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
    @property
    def required_candles(self) -> int:
        return 100
    
    def _find_swings(self, df: pd.DataFrame, window: int = 2) -> Dict[str, List[int]]:
        """BOS often uses more significant swings, so window=5 is default here."""
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
            
        last_h = df['high'].iloc[high_indices[-1]]
        last_l = df['low'].iloc[low_indices[-1]]
        
        # We also need the previous HL/LH for SL placement
        prev_h = df['high'].iloc[high_indices[-2]]
        prev_l = df['low'].iloc[low_indices[-2]]
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        signals = []
        
        # Average body size for displacement check
        avg_body = (df['close'] - df['open']).abs().tail(20).mean()
        current_body = abs(current_candle['close'] - current_candle['open'])
        
        # Average volume for confirmation
        avg_vol = df['volume'].tail(20).mean()
        current_vol = current_candle['volume']
        
        displacement = current_body > (avg_body * 1.5)
        vol_confirmation = current_vol > avg_vol
        
        # Bullish BOS: Close above last HH
        if current_candle['close'] > last_h and prev_candle['close'] <= last_h:
            confidence = 0.7
            if displacement: confidence += 0.1
            if vol_confirmation: confidence += 0.1
            
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=min(confidence, 1.0),
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=last_l, # SL below recent HL
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish BOS: Price closed above previous high ({last_h:.2f}). "
                          f"Displacement: {'Strong' if displacement else 'Normal'}. "
                          f"Volume: {'Confirmed' if vol_confirmation else 'Normal'}."
            ))
            
        # Bearish BOS: Close below last LL
        elif current_candle['close'] < last_l and prev_candle['close'] >= last_l:
            confidence = 0.7
            if displacement: confidence += 0.1
            if vol_confirmation: confidence += 0.1
            
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=min(confidence, 1.0),
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=last_h, # SL above recent LH
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish BOS: Price closed below previous low ({last_l:.2f}). "
                          f"Displacement: {'Strong' if displacement else 'Normal'}. "
                          f"Volume: {'Confirmed' if vol_confirmation else 'Normal'}."
            ))
            
        return signals
