"""
Strategy: Horizontal Channel Pattern (Rectangle / Range)
Category: price_action_pattern
Source: Price action patterns/RECTANGLE ,RANGE PATTERNS.md

Description:
  A range-bound structure with parallel horizontal support and resistance lines.
  - Resistance: Flat line connecting multiple peaks.
  - Support: Flat line connecting multiple troughs.

Logic:
  - Both slopes must be near zero.
  - Multiple touches on both boundaries.
  - Signals: Mean reversion near edges or breakouts.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class HorizontalChannel(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Horizontal Channel"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Boundaries using rolling extremes
        # Use a window to find the most frequent high/low levels
        window = 20
        rolling_max = df['high'].rolling(window=window).max().tail(60)
        rolling_min = df['low'].rolling(window=window).min().tail(60)
        
        resistance = rolling_max.value_counts().idxmax()
        support = rolling_min.value_counts().idxmax()
        
        range_height = resistance - support
        if range_height <= 0: return []
        
        # 2. Verify Horizontal Structure
        # Check if the rolling extremes are relatively stable (slopes near 0)
        h_slope, _ = np.polyfit(np.arange(len(rolling_max.dropna())), rolling_max.dropna().values, 1)
        l_slope, _ = np.polyfit(np.arange(len(rolling_min.dropna())), rolling_min.dropna().values, 1)
        
        is_horizontal = abs(h_slope) < 0.05 and abs(l_slope) < 0.05
        
        if not is_horizontal:
            return []
            
        # 3. Check for multiple touches (at least 2 on each side)
        high_touches = (df['high'].tail(60) >= resistance * 0.998).sum()
        low_touches = (df['low'].tail(60) <= support * 1.002).sum()
        
        if high_touches < 2 or low_touches < 2:
            return []
            
        current_price = df['close'].iloc[-1]
        signals = []
        
        # 4. Entry Logic
        # A. Buy near Support
        if current_price >= support and current_price <= (support + range_height * 0.2):
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=support * 0.995,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Price near Horizontal Channel support ({support:.2f})."
            ))
        # B. Sell near Resistance
        elif current_price <= resistance and current_price >= (resistance - range_height * 0.2):
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=resistance * 1.005,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Price near Horizontal Channel resistance ({resistance:.2f})."
            ))
        # C. Bullish Breakout
        elif current_price > resistance:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=resistance * 0.995,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Breakout above Horizontal Channel ({resistance:.2f})."
            ))
        # D. Bearish Breakdown
        elif current_price < support:
            signals.append(Signal(
                signal_type=SignalType.STRONG_SELL,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=support * 1.005,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Breakdown below Horizontal Channel ({support:.2f})."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.5,
                timeframe=timeframe,
                market_bias=MarketBias.NEUTRAL,
                reasoning="Within Horizontal Channel."
            ))
            
        return signals
