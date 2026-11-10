"""
Strategy: Hammer Candlestick Pattern
Category: candlestick
Source: Candlestickpatterns/Hammer Candlestick Pattern.md

Description:
  A single-candle bullish reversal pattern.
  - Small body at the top of the range.
  - Long lower wick (at least 2x body size).
  - Little or no upper wick.

Logic:
  - Must occur after a prior downtrend.
  - Rejection of lower prices indicates institutional buying.
  - High volume on the hammer increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class Hammer(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Hammer"
    
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
        
        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        
        if total_range == 0:
            return []
            
        lower_wick = min(c['open'], c['close']) - c['low']
        upper_wick = c['high'] - max(c['open'], c['close'])
        
        # Hammer Conditions:
        # 1. Lower wick >= 2 * body
        # 2. Upper wick is very small
        is_hammer = (lower_wick >= 2 * body_size) and (upper_wick <= total_range * 0.1)
        
        if not is_hammer:
            return []
            
        # Check for prior downtrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_downtrend = c['close'] < sma_fast.iloc[-1] or c['close'] < df['close'].iloc[-10]
        
        if not prior_downtrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c['volume'] > avg_vol
        
        confidence = 0.7
        if vol_spike: confidence += 0.1
        if c['close'] > c['open']: confidence += 0.05 # Bullish body is stronger
            
        signals = [Signal(
            signal_type=SignalType.BUY,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c['close'],
            stop_loss=c['low'],
            market_bias=MarketBias.BULLISH,
            reasoning=f"Hammer detected after downtrend. Strong rejection of lower prices (Wick: {lower_wick/body_size if body_size > 0 else 'inf':.1f}x body)."
        )]
        
        return signals
