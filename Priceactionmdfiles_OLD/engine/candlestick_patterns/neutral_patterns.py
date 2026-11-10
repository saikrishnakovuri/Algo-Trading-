"""
Strategy: Neutral Candlestick Price Action Patterns
Category: candlestick
Source: Candlestickpatterns/Neutral Candlestick Price Action Patterns.md

Description:
  Price action structures representing indecision, balance, and volatility compression.
  Includes: Spinning Top, Inside Bar, High Wave, NR4/NR7.

Logic:
  - Spinning Top: Small body, symmetrical wicks.
  - Inside Bar: Range remains within the previous candle's range.
  - High Wave: Small body, extremely long wicks.
  - NR7: Narrowest range of the last 7 candles.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class NeutralPatterns(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Neutral Patterns"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 20
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        c = df.iloc[-1]
        p = df.iloc[-2]
        
        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        if total_range == 0: return []
        
        signals = []
        
        # 1. Inside Bar
        is_inside_bar = (c['high'] <= p['high']) and (c['low'] >= p['low'])
        if is_inside_bar:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.5,
                timeframe=timeframe,
                market_bias=MarketBias.NEUTRAL,
                reasoning="Inside Bar detected. Volatility compression, awaiting breakout."
            ))
            
        # 2. Spinning Top
        # Small body (<= 20% range) and balanced wicks
        upper_wick = c['high'] - max(c['open'], c['close'])
        lower_wick = min(c['open'], c['close']) - c['low']
        is_spinning_top = (body_size <= total_range * 0.2) and \
                          (0.8 <= (upper_wick / lower_wick) <= 1.2 if lower_wick > 0 else False)
        if is_spinning_top and not is_inside_bar:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.5,
                timeframe=timeframe,
                market_bias=MarketBias.NEUTRAL,
                reasoning="Spinning Top detected. Market equilibrium."
            ))
            
        # 3. High Wave
        # Small body and very long wicks (range > 2x average)
        avg_range = (df['high'] - df['low']).tail(20).mean()
        is_high_wave = (body_size <= total_range * 0.2) and (total_range > avg_range * 2.0)
        if is_high_wave:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.VOLATILE,
                reasoning="High Wave candle detected. High uncertainty and volatility."
            ))
            
        # 4. NR7 (Narrow Range 7)
        ranges = (df['high'] - df['low']).tail(7)
        if total_range == ranges.min():
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.NEUTRAL,
                reasoning="NR7 (Narrowest Range in 7 candles) detected. Extreme volatility contraction."
            ))
            
        return signals
