"""
Strategy: Rectangle / Range Pattern
Category: price_action_pattern
Source: Price action patterns/RECTANGLE ,RANGE PATTERNS.md

Description:
  A sideways consolidation structure with flat support and resistance.
  - Signal occurs at boundary rejections or breakouts.

Logic:
  - Both slopes must be near zero (horizontal).
  - Multiple touches on both boundaries (at least 2).
  - Breakout occurs above resistance or below support.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class RectangleRange(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Rectangle Range"
    
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
        window = 20
        rolling_max = df['high'].rolling(window=window).max().tail(60)
        rolling_min = df['low'].rolling(window=window).min().tail(60)
        
        if rolling_max.empty or rolling_min.empty: return []
        
        resistance = rolling_max.value_counts().idxmax()
        support = rolling_min.value_counts().idxmax()
        
        range_height = resistance - support
        if range_height <= 0: return []
        
        # 2. Verify Horizontal Structure
        h_slope, _ = np.polyfit(np.arange(len(rolling_max.dropna())), rolling_max.dropna().values, 1)
        l_slope, _ = np.polyfit(np.arange(len(rolling_min.dropna())), rolling_min.dropna().values, 1)
        
        if abs(h_slope) > 0.05 or abs(l_slope) > 0.05:
            return []
            
        # 3. Check for multiple touches
        high_touches = (df['high'].tail(60) >= resistance * 0.998).sum()
        low_touches = (df['low'].tail(60) <= support * 1.002).sum()
        
        if high_touches < 2 or low_touches < 2:
            return []
            
        current_price = df['close'].iloc[-1]
        signals = []
        
        # 4. Entry Logic
        if current_price > resistance:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=resistance * 0.995,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Rectangle Breakout above {resistance:.2f}."
            ))
        elif current_price < support:
            signals.append(Signal(
                signal_type=SignalType.STRONG_SELL,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=support * 1.005,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Rectangle Breakdown below {support:.2f}."
            ))
        elif current_price >= support and current_price <= (support + range_height * 0.2):
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=support * 0.99,
                market_bias=MarketBias.BULLISH,
                reasoning=f"Range Trade: Buying near support ({support:.2f})."
            ))
        elif current_price <= resistance and current_price >= (resistance - range_height * 0.2):
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=resistance * 1.01,
                market_bias=MarketBias.BEARISH,
                reasoning=f"Range Trade: Selling near resistance ({resistance:.2f})."
            ))
            
        return signals
