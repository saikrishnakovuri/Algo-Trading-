"""
Strategy: Ascending Channel Pattern
Category: price_action_pattern
Source: Price action patterns/Ascending Channel Pattern.md

Description:
  A bullish trend structure contained within two parallel upward-sloping trendlines.
  - Support line: Connects higher lows.
  - Resistance line: Connects higher highs.

Logic:
  - Higher highs and higher lows required.
  - Trendlines must be relatively parallel (similar slopes).
  - Multiple touches on both boundaries increase validity.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class AscendingChannel(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Ascending Channel"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
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
        
        # Need at least 2 points to draw a line
        if len(high_indices) < 2 or len(low_indices) < 2:
            return []
            
        # 1. Fit trendlines through recent swing points
        recent_h_idx = high_indices[-5:]
        recent_l_idx = low_indices[-5:]
        
        h_prices = df['high'].iloc[recent_h_idx].values
        l_prices = df['low'].iloc[recent_l_idx].values
        
        # Linear regression
        h_slope, h_intercept = np.polyfit(recent_h_idx, h_prices, 1)
        l_slope, l_intercept = np.polyfit(recent_l_idx, l_prices, 1)
        
        # 2. Check for Ascending structure
        if h_slope <= 0 or l_slope <= 0:
            return []
            
        # 3. Check for Parallelism
        avg_slope = (h_slope + l_slope) / 2
        slope_diff = abs(h_slope - l_slope) / max(abs(avg_slope), 0.001)
        
        if slope_diff > 0.8: # Relaxed for variety
            return []
            
        current_idx = len(df) - 1
        current_price = df['close'].iloc[-1]
        
        expected_high = h_slope * current_idx + h_intercept
        expected_low = l_slope * current_idx + l_intercept
        
        signals = []
        
        if current_price >= expected_low and current_price <= (expected_low + (expected_high - expected_low) * 0.3):
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.75,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=expected_low * 0.995,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Price is near Ascending Channel support ({expected_low:.2f})."
            ))
        elif current_price > expected_high:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=expected_high * 0.995,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish Breakout from Ascending Channel high ({expected_high:.2f})."
            ))
        elif current_price < expected_low:
             signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=expected_low * 1.005,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish Breakdown from Ascending Channel support ({expected_low:.2f})."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BULLISH,
                reasoning="Within an established Ascending Channel."
            ))
            
        return signals
