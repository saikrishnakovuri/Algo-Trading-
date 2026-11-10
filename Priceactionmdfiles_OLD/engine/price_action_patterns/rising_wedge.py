"""
Strategy: Rising Wedge Pattern
Category: price_action_pattern
Source: Price action patterns/Rising Wedge Pattern.md

Description:
  A bearish reversal/continuation pattern with two converging upward trendlines.
  - Support: Rising faster than resistance.
  - Resistance: Rising slower than support.

Logic:
  - Requires higher highs and higher lows.
  - Trendlines must converge (slope of support > slope of resistance).
  - Breakdown occurs below the support trendline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class RisingWedge(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Rising Wedge"
    
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
        
        # 3. Check for Rising Wedge structure
        # Both must be rising
        is_rising = h_slope > 0.001 and l_slope > 0.001
        
        # Convergence: Support rising faster than resistance
        # Note: both are positive, so l_slope > h_slope means they converge
        is_converging = l_slope > h_slope
        
        if not (is_rising and is_converging):
            return []
            
        current_price = df['close'].iloc[-1]
        # Expected support should be based on troughs BEFORE current candle
        expected_sup = data['low'].iloc[-10:-1].min()
        
        signals = []
        
        if current_price < expected_sup:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=h_end,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Rising Wedge Breakdown. Price {current_price:.2f} < Support {expected_sup:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BEARISH,
                reasoning="Inside Rising Wedge structure."
            ))
            
        return signals
