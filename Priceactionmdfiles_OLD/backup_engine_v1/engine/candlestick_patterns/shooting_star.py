"""
Strategy: Shooting Star Candlestick Pattern
Category: candlestick
Source: Candlestickpatterns/Shooting Star Pattern.md

Description:
  A single-candle bearish reversal pattern.
  - Small body at the bottom of the range.
  - Long upper wick (at least 2x body size).
  - Little or no lower wick.

Logic:
  - Must occur after a prior uptrend.
  - Rejection of higher prices indicates institutional distribution.
  - High volume on the shooting star increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class ShootingStar(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Shooting Star"
    
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
            
        upper_wick = c['high'] - max(c['open'], c['close'])
        lower_wick = min(c['open'], c['close']) - c['low']
        
        # Shooting Star Conditions:
        # 1. Upper wick >= 2 * body
        # 2. Lower wick is very small
        is_shooting_star = (upper_wick >= 2 * body_size) and (lower_wick <= total_range * 0.1)
        
        if not is_shooting_star:
            return []
            
        # Check for prior uptrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_uptrend = c['close'] > sma_fast.iloc[-1] or c['close'] > df['close'].iloc[-10]
        
        if not prior_uptrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c['volume'] > avg_vol
        
        confidence = 0.7
        if vol_spike: confidence += 0.1
        if c['close'] < c['open']: confidence += 0.05 # Bearish body is stronger
            
        signals = [Signal(
            signal_type=SignalType.SELL,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c['close'],
            stop_loss=c['high'],
            market_bias=MarketBias.BEARISH,
            reasoning=f"Shooting Star detected after uptrend. Strong rejection of higher prices (Wick: {upper_wick/body_size if body_size > 0 else 'inf':.1f}x body)."
        )]
        
        return signals
