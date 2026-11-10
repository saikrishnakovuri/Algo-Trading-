"""
Strategy: Falling Wedge Pattern
Category: price_action_pattern
Source: Price action patterns/Falling Wedge Pattern.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class FallingWedge(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Falling Wedge"
    
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
        h_end = data['high'].iloc[-10:].max()
        h_slope = (h_end - h_start) / window
        
        # Support (Lows)
        l_start = data['low'].iloc[:10].min()
        l_end = data['low'].iloc[-10:].min()
        l_slope = (l_end - l_start) / window
        
        # 3. Check for Falling Wedge structure
        # Both must be falling
        is_falling = h_slope < -0.001 and l_slope < -0.001
        # Range should be narrowing
        is_converging = h_slope < l_slope
        
        if not (is_falling and is_converging):
            return []
            
        current_price = df['close'].iloc[-1]
        # Expected resistance should be based on peaks BEFORE current candle
        expected_res = data['high'].iloc[-10:-1].max()
        
        signals = []
        
        if current_price > expected_res:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=l_end,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Falling Wedge Breakout. Price {current_price:.2f} > Resistance {expected_res:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BULLISH,
                reasoning="Inside Falling Wedge structure."
            ))
            
        return signals
