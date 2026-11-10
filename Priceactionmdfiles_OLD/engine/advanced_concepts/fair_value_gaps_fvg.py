"""
Strategy: Fair Value Gaps (FVG)
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Fair Value Gaps (FVG).md

Description:
  Fair Value Gaps represent market imbalance created by strong displacement.
  - Bullish FVG: Candle 3 Low > Candle 1 High.
  - Bearish FVG: Candle 3 High < Candle 1 Low.

Logic:
  - Usually a 3-candle pattern.
  - The middle candle (Candle 2) is the displacement candle.
  - Markets tend to return to these zones to "fill" the imbalance.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class FairValueGaps(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Fair Value Gaps (FVG)"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
    @property
    def required_candles(self) -> int:
        return 50
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        signals = []
        
        # Check the last 10 candles for FVG formation or mitigation
        # We need at least 3 candles to identify a gap
        for i in range(len(df) - 10, len(df) - 1):
            if i < 2: continue
            
            c1 = df.iloc[i-2]
            c2 = df.iloc[i-1]
            c3 = df.iloc[i]
            
            # Average body for displacement check
            avg_body = (df['close'] - df['open']).abs().iloc[max(0, i-20):i-1].mean()
            c2_body = abs(c2['close'] - c2['open'])
            displacement = c2_body > (avg_body * 1.5)
            
            # Bullish FVG
            if c3['low'] > c1['high'] and c2['close'] > c2['open'] and displacement:
                gap_low = c1['high']
                gap_high = c3['low']
                current_price = df['close'].iloc[-1]
                
                # Check if current price is in the gap (mitigation)
                if current_price >= gap_low and current_price <= gap_high:
                    signals.append(Signal(
                        signal_type=SignalType.BUY,
                        strategy_name=self.name,
                        confidence=0.75,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=gap_low,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Bullish FVG Mitigation: Price is currently within a gap zone ({gap_low:.2f} - {gap_high:.2f})."
                    ))
                elif current_price > gap_high:
                    # Still a valid imbalance ahead
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.6,
                        timeframe=timeframe,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Bullish FVG detected at {gap_low:.2f}-{gap_high:.2f}. Potential support on pullback."
                    ))
            
            # Bearish FVG
            elif c3['high'] < c1['low'] and c2['close'] < c2['open'] and displacement:
                gap_high = c1['low']
                gap_low = c3['high']
                current_price = df['close'].iloc[-1]
                
                if current_price >= gap_low and current_price <= gap_high:
                    signals.append(Signal(
                        signal_type=SignalType.SELL,
                        strategy_name=self.name,
                        confidence=0.75,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=gap_high,
                        market_bias=MarketBias.BEARISH,
                        reasoning=f"Bearish FVG Mitigation: Price is currently within a gap zone ({gap_low:.2f} - {gap_high:.2f})."
                    ))
                elif current_price < gap_low:
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.6,
                        timeframe=timeframe,
                        market_bias=MarketBias.BEARISH,
                        reasoning=f"Bearish FVG detected at {gap_low:.2f}-{gap_high:.2f}. Potential resistance on rally."
                    ))
                    
        return signals
