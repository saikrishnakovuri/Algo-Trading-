"""
Strategy: Order Blocks
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Order Blocks.md

Description:
  Order Blocks are institutional buying or selling zones.
  - Bullish OB: The last bearish candle before a strong bullish impulsive move (BOS).
  - Bearish OB: The last bullish candle before a strong bearish impulsive move (BOS).

Logic:
  - Requires "displacement" (large candles, high volume).
  - Validated when price breaks structure (BOS).
  - Entry occurs when price revisits (mitigates) the order block zone.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class OrderBlocks(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Order Blocks"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
    @property
    def required_candles(self) -> int:
        return 100
    
    def _find_swings(self, df: pd.DataFrame, window: int = 3) -> Dict[str, List[int]]:
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
        
        if len(high_indices) < 1 or len(low_indices) < 1:
            return []
            
        signals = []
        
        # We look for a recent displacement that broke a swing point
        # Let's check the last 10 candles for a displacement start
        for i in range(len(df) - 10, len(df)):
            candle = df.iloc[i]
            prev_candle = df.iloc[i-1]
            
            # Displacement check
            avg_body = (df['close'] - df['open']).abs().iloc[max(0, i-20):i].mean()
            current_body = abs(candle['close'] - candle['open'])
            displacement = current_body > (avg_body * 2.0)
            
            if not displacement:
                continue
                
            # Bullish Displacement
            if candle['close'] > candle['open']:
                # Find if it broke a recent swing high
                recent_highs = [h for h in high_indices if h < i and h > i - 20]
                if recent_highs:
                    last_swing_h = df['high'].iloc[recent_highs[-1]]
                    if candle['close'] > last_swing_h:
                        # Bullish OB is the last bearish candle before this move
                        # Look back for the nearest bearish candle
                        for j in range(i-1, i-5, -1):
                            if df['close'].iloc[j] < df['open'].iloc[j]:
                                ob_candle = df.iloc[j]
                                ob_zone_high = ob_candle['high']
                                ob_zone_low = ob_candle['low']
                                
                                # Current price might be mitigating it now
                                current_price = df['close'].iloc[-1]
                                if current_price >= ob_zone_low and current_price <= ob_zone_high:
                                    signals.append(Signal(
                                        signal_type=SignalType.BUY,
                                        strategy_name=self.name,
                                        confidence=0.8,
                                        timeframe=timeframe,
                                        entry_price=current_price,
                                        stop_loss=ob_zone_low,
                                        market_bias=MarketBias.BULLISH,
                                        reasoning=f"Bullish Order Block Mitigation: Price revisited the zone ({ob_zone_low:.2f} - {ob_zone_high:.2f}) created before a BOS."
                                    ))
                                elif current_price > ob_zone_high:
                                    # Still valid but not in zone
                                    signals.append(Signal(
                                        signal_type=SignalType.HOLD,
                                        strategy_name=self.name,
                                        confidence=0.6,
                                        timeframe=timeframe,
                                        market_bias=MarketBias.BULLISH,
                                        reasoning=f"Bullish Order Block identified at {ob_zone_low:.2f}-{ob_zone_high:.2f}. Awaiting mitigation."
                                    ))
                                break
                                
            # Bearish Displacement
            elif candle['close'] < candle['open']:
                # Find if it broke a recent swing low
                recent_lows = [l for l in low_indices if l < i and l > i - 20]
                if recent_lows:
                    last_swing_l = df['low'].iloc[recent_lows[-1]]
                    if candle['close'] < last_swing_l:
                        # Bearish OB is the last bullish candle before this move
                        for j in range(i-1, i-5, -1):
                            if df['close'].iloc[j] > df['open'].iloc[j]:
                                ob_candle = df.iloc[j]
                                ob_zone_high = ob_candle['high']
                                ob_zone_low = ob_candle['low']
                                
                                current_price = df['close'].iloc[-1]
                                if current_price >= ob_zone_low and current_price <= ob_zone_high:
                                    signals.append(Signal(
                                        signal_type=SignalType.SELL,
                                        strategy_name=self.name,
                                        confidence=0.8,
                                        timeframe=timeframe,
                                        entry_price=current_price,
                                        stop_loss=ob_zone_high,
                                        market_bias=MarketBias.BEARISH,
                                        reasoning=f"Bearish Order Block Mitigation: Price revisited the zone ({ob_zone_low:.2f} - {ob_zone_high:.2f}) created before a BOS."
                                    ))
                                elif current_price < ob_zone_low:
                                    signals.append(Signal(
                                        signal_type=SignalType.HOLD,
                                        strategy_name=self.name,
                                        confidence=0.6,
                                        timeframe=timeframe,
                                        market_bias=MarketBias.BEARISH,
                                        reasoning=f"Bearish Order Block identified at {ob_zone_low:.2f}-{ob_zone_high:.2f}. Awaiting mitigation."
                                    ))
                                break
                                
        return signals
