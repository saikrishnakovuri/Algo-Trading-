"""
Strategy: Symmetrical Triangle Pattern
Category: price_action_pattern
Source: Price action patterns/symmetricaltrianglepattern.md

Description:
  A neutral consolidation pattern with two converging trendlines.
  - Resistance: Lower highs (negative slope).
  - Support: Higher lows (positive slope).

Logic:
  - Requires price compression (narrowing range).
  - Breakdown occurs below support, breakout above resistance.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class SymmetricalTriangle(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Symmetrical Triangle"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # Use simple difference over window for slopes
        window = 60
        data = df.tail(window)
        
        # Resistance (Highs)
        h_start = data['high'].iloc[:10].max()
        h_end = data['high'].iloc[-10:-1].max() # Exclude current
        h_slope = (h_end - h_start) / window
        
        # Support (Lows)
        l_start = data['low'].iloc[:10].min()
        l_end = data['low'].iloc[-10:-1].min() # Exclude current
        l_slope = (l_end - l_start) / window
        
        # 3. Check for Symmetrical structure
        # Resistance must be falling, Support must be rising
        is_falling_res = h_slope < -0.001
        is_rising_sup = l_slope > 0.001
        
        # Convergence: Range should be narrowing
        range_start = h_start - l_start
        range_end = h_end - l_end
        is_converging = range_end < range_start * 0.9
        
        if not (is_falling_res and is_rising_sup and is_converging):
            return []
            
        current_price = df['close'].iloc[-1]
        signals = []
        
        # 4. Breakout Logic
        # A. Bullish Breakout
        if current_price > h_end:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=l_end,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Symmetrical Triangle Bullish Breakout above {h_end:.2f}."
            ))
        # B. Bearish Breakdown
        elif current_price < l_end:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=h_end,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Symmetrical Triangle Bearish Breakdown below {l_end:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.NEUTRAL,
                reasoning="Inside Symmetrical Triangle compression."
            ))
            
        return signals
