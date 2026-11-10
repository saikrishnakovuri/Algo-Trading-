"""
Strategy: Supply & Demand
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Supply & Demand.md

Description:
  Supply & Demand zones are the origin of strong impulsive moves.
  - Demand Zone: Consolidation before a strong bullish expansion (Rally).
  - Supply Zone: Consolidation before a strong bearish expansion (Drop).

Logic:
  - Requires a "Base" (consolidation) and a "Departure" (displacement).
  - Validated when the departure breaks structure (BOS).
  - Entry occurs on the first return to the zone (Fresh Zone).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class SupplyDemand(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Supply & Demand"
    
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
        
        signals = []
        current_price = df['close'].iloc[-1]
        
        # Look for recent supply/demand zones
        # We check the last 20 candles for a departure
        for i in range(len(df) - 20, len(df)):
            candle = df.iloc[i]
            
            # Displacement check
            avg_body = (df['close'] - df['open']).abs().iloc[max(0, i-20):i].mean()
            current_body = abs(candle['close'] - candle['open'])
            if current_body < (avg_body * 2.0):
                continue
                
            # Departure detected at index i
            # Identify the "Base" (last 1-3 candles before i)
            base_indices = range(max(0, i-3), i)
            base_high = df['high'].iloc[base_indices].max()
            base_low = df['low'].iloc[base_indices].min()
            
            # Bullish Departure -> Potential Demand Zone
            if candle['close'] > candle['open']:
                # Must break a recent swing high
                recent_highs = [h for h in high_indices if h < i and h > i - 30]
                if recent_highs:
                    last_sh = df['high'].iloc[recent_highs[-1]]
                    if candle['close'] > last_sh:
                        # Zone is [base_low, base_high]
                        if current_price >= base_low and current_price <= base_high:
                            signals.append(Signal(
                                signal_type=SignalType.BUY,
                                strategy_name=self.name,
                                confidence=0.8,
                                timeframe=timeframe,
                                entry_price=current_price,
                                stop_loss=base_low,
                                market_bias=MarketBias.BULLISH,
                                reasoning=f"Demand Zone Retest: Price revisited the base ({base_low:.2f} - {base_high:.2f}) that created a Bullish BOS."
                            ))
                        elif current_price > base_high:
                            signals.append(Signal(
                                signal_type=SignalType.HOLD,
                                strategy_name=self.name,
                                confidence=0.6,
                                timeframe=timeframe,
                                market_bias=MarketBias.BULLISH,
                                reasoning=f"Demand Zone identified at {base_low:.2f}-{base_high:.2f}. Awaiting retest."
                            ))
                            
            # Bearish Departure -> Potential Supply Zone
            elif candle['close'] < candle['open']:
                # Must break a recent swing low
                recent_lows = [l for l in low_indices if l < i and l > i - 30]
                if recent_lows:
                    last_sl = df['low'].iloc[recent_lows[-1]]
                    if candle['close'] < last_sl:
                        # Zone is [base_low, base_high]
                        if current_price >= base_low and current_price <= base_high:
                            signals.append(Signal(
                                signal_type=SignalType.SELL,
                                strategy_name=self.name,
                                confidence=0.8,
                                timeframe=timeframe,
                                entry_price=current_price,
                                stop_loss=base_high,
                                market_bias=MarketBias.BEARISH,
                                reasoning=f"Supply Zone Retest: Price revisited the base ({base_low:.2f} - {base_high:.2f}) that created a Bearish BOS."
                            ))
                        elif current_price < base_low:
                            signals.append(Signal(
                                signal_type=SignalType.HOLD,
                                strategy_name=self.name,
                                confidence=0.6,
                                timeframe=timeframe,
                                market_bias=MarketBias.BEARISH,
                                reasoning=f"Supply Zone identified at {base_low:.2f}-{base_high:.2f}. Awaiting retest."
                            ))
                            
        return signals
