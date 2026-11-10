"""
Strategy: Change of Character (CHOCH)
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/hange of Character (CHOCH).md

Description:
  CHOCH represents early trend reversal indication.
  - Bullish CHOCH: During a bearish trend, price breaks the previous Lower High (LH).
  - Bearish CHOCH: During a bullish trend, price breaks the previous Higher Low (HL).

Logic:
  - Signifies a shift in institutional control.
  - Requires displacement and volume for high-probability signals.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class ChangeOfCharacter(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Change of Character (CHOCH)"
    
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
            
        last_h = df['high'].iloc[high_indices[-1]]
        prev_h = df['high'].iloc[high_indices[-2]]
        last_l = df['low'].iloc[low_indices[-1]]
        prev_l = df['low'].iloc[low_indices[-2]]
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Determine current trend bias based on previous swings
        # Downtrend: LH2 < LH1 or LL2 < LL1 (at least one confirmed)
        is_bearish_trend = last_h < prev_h or last_l < prev_l
        # Uptrend: HH2 > HH1 or HL2 > HL1
        is_bullish_trend = last_h > prev_h or last_l > prev_l
        
        # Avoid neutral/choppy markets where both could be true if not careful
        # But here we want to catch the shift.
            
        signals = []
        
        # Average body size for displacement check
        avg_body = (df['close'] - df['open']).abs().tail(20).mean()
        current_body = abs(current_candle['close'] - current_candle['open'])
        
        # Average volume for confirmation
        avg_vol = df['volume'].tail(20).mean()
        current_vol = current_candle['volume']
        
        displacement = current_body > (avg_body * 1.5)
        vol_confirmation = current_vol > avg_vol
        
        # Bullish CHOCH: Break LH in bearish trend
        if is_bearish_trend and current_candle['close'] > last_h and prev_candle['close'] <= last_h:
            confidence = 0.75
            if displacement: confidence += 0.1
            if vol_confirmation: confidence += 0.1
            
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=min(confidence, 1.0),
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=last_l, # SL below the LL
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish CHOCH: Price broke Lower High ({last_h:.2f}) in a Bearish Trend. "
                          f"Displacement: {'Strong' if displacement else 'Normal'}. "
                          f"Volume: {'Confirmed' if vol_confirmation else 'Normal'}."
            ))
            
        # Bearish CHOCH: Break HL in bullish trend
        elif is_bullish_trend and current_candle['close'] < last_l and prev_candle['close'] >= last_l:
            confidence = 0.75
            if displacement: confidence += 0.1
            if vol_confirmation: confidence += 0.1
            
            signals.append(Signal(
                signal_type=SignalType.STRONG_SELL,
                strategy_name=self.name,
                confidence=min(confidence, 1.0),
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=last_h, # SL above the HH
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish CHOCH: Price broke Higher Low ({last_l:.2f}) in a Bullish Trend. "
                          f"Displacement: {'Strong' if displacement else 'Normal'}. "
                          f"Volume: {'Confirmed' if vol_confirmation else 'Normal'}."
            ))
            
        return signals
