"""
Strategy: Descending Channel Pattern
Category: price_action_pattern
Source: Price action patterns/Descending Channel Pattern.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class DescendingChannel(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Descending Channel"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Upper Boundary (Resistance)
        rolling_max = df['high'].rolling(window=20).max().tail(60).dropna()
        if len(rolling_max) < 2: return []
        h_x = np.arange(len(rolling_max))
        h_slope, h_intercept = np.polyfit(h_x, rolling_max.values, 1)
        
        # 2. Identify Lower Boundary (Support)
        rolling_min = df['low'].rolling(window=20).min().tail(60).dropna()
        if len(rolling_min) < 2: return []
        l_x = np.arange(len(rolling_min))
        l_slope, l_intercept = np.polyfit(l_x, rolling_min.values, 1)
        
        # 3. Check for Descending Parallel structure
        is_descending = h_slope < -0.001 and l_slope < -0.001
        avg_slope = (h_slope + l_slope) / 2
        slope_diff = abs(h_slope - l_slope) / max(abs(avg_slope), 0.001)
        
        if not is_descending or slope_diff > 0.8:
            return []
            
        current_idx = 59 # Last index of tail(60)
        expected_high = h_slope * current_idx + h_intercept
        expected_low = l_slope * current_idx + l_intercept
        current_price = df['close'].iloc[-1]
        
        signals = []
        
        if current_price <= expected_high and current_price >= (expected_high - (expected_high - expected_low) * 0.5):
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.75,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=expected_high * 1.01,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Price is near Descending Channel resistance ({expected_high:.2f})."
            ))
        elif current_price > expected_high:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=expected_high * 0.99,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish Breakout from Descending Channel."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BEARISH,
                reasoning="Within an established Descending Channel."
            ))
            
        return signals
