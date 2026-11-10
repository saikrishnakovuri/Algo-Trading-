"""
Strategy: Ascending Triangle Pattern
Category: price_action_pattern
Source: Price action patterns/Ascending Triangle Pattern.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class AscendingTriangle(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Ascending Triangle"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Resistance Level
        # Use rolling max to find consistent peaks
        rolling_max = df['high'].rolling(window=20).max()
        # Find levels where rolling max is nearly constant
        # We'll check the last 60 candles
        last_peaks = rolling_max.tail(60)
        resistance_level = last_peaks.value_counts().idxmax()
        peak_count = (df['high'].tail(60) >= resistance_level * 0.998).sum()
        
        # 2. Identify Rising Support
        # Use rolling min to find rising lows
        rolling_min = df['low'].rolling(window=20).min()
        last_lows = rolling_min.tail(60).dropna()
        if len(last_lows) < 2: return []
        
        # Linear regression on rolling lows to find trend
        low_x = np.arange(len(last_lows))
        low_slope, low_intercept = np.polyfit(low_x, last_lows.values, 1)
        
        is_ascending = low_slope > 0.001
        is_compressed = peak_count >= 3
        
        if not (is_ascending and is_compressed):
            return []
            
        current_price = df['close'].iloc[-1]
        signals = []
        
        # 3. Breakout Logic
        if current_price > resistance_level:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=resistance_level * 0.99,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Ascending Triangle Breakout above {resistance_level:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Inside Ascending Triangle. Resistance: {resistance_level:.2f}. Support is rising."
            ))
            
        return signals
