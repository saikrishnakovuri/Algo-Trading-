"""
Strategy: Descending Triangle Pattern
Category: price_action_pattern
Source: Price action patterns/Descending Triangle Pattern.md

Description:
  A bearish continuation pattern with flat horizontal support and falling resistance.
  - Support: Connects nearly equal lows.
  - Resistance: Connects lower highs (negative slope).

Logic:
  - Requires horizontal support tested multiple times.
  - Requires downward sloping resistance line.
  - Volume typically contracts during formation and expands on breakdown.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class DescendingTriangle(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Descending Triangle"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Support Level
        # Use rolling min to find consistent troughs
        rolling_min = df['low'].rolling(window=20).min()
        last_lows = rolling_min.tail(60)
        support_level = last_lows.value_counts().idxmax()
        low_count = (df['low'].tail(60) <= support_level * 1.002).sum()
        
        # 2. Identify Falling Resistance
        # Use rolling max to find lower highs
        rolling_max = df['high'].rolling(window=20).max()
        last_highs = rolling_max.tail(60).dropna()
        if len(last_highs) < 2: return []
        
        high_x = np.arange(len(last_highs))
        high_slope, high_intercept = np.polyfit(high_x, last_highs.values, 1)
        
        is_descending = high_slope < -0.001
        is_compressed = low_count >= 3
        
        if not (is_descending and is_compressed):
            return []
            
        current_price = df['close'].iloc[-1]
        signals = []
        
        # 3. Breakdown Logic
        if current_price < support_level:
            avg_vol = df['volume'].tail(20).mean()
            vol_spike = df['volume'].iloc[-1] > avg_vol
            
            signals.append(Signal(
                signal_type=SignalType.STRONG_SELL,
                strategy_name=self.name,
                confidence=0.85 if vol_spike else 0.75,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=support_level * 1.01,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Descending Triangle Breakdown below {support_level:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Inside Descending Triangle. Support: {support_level:.2f}. Resistance is falling."
            ))
            
        return signals
