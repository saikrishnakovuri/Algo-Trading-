"""
Strategy: Piercing Pattern
Category: candlestick
Source: Candlestickpatterns/Piercing Pattern.md

Description:
  A two-candle bullish reversal pattern.
  - Candle 1: Strong bearish candle.
  - Candle 2: Bullish candle that opens below Candle 1's close and closes above its midpoint.

Logic:
  - Must occur after a prior downtrend.
  - Candle 2 must close deep into Candle 1's body (at least above 50%).
  - Higher volume on Candle 2 increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class PiercingPattern(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Piercing Pattern"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 20
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        c1 = df.iloc[-2]
        c2 = df.iloc[-1]
        
        # Candle 1 must be strongly Bearish
        c1_bearish = c1['close'] < c1['open']
        # Candle 2 must be Bullish
        c2_bullish = c2['close'] > c2['open']
        
        if not (c1_bearish and c2_bullish):
            return []
            
        # 1. Gap down: C2 open < C1 close
        gap_down = c2['open'] < c1['close']
        
        # 2. Closes above midpoint: C2 close > (C1 open + C1 close) / 2
        midpoint = (c1['open'] + c1['close']) / 2
        above_midpoint = c2['close'] > midpoint
        
        # 3. Optional: Should NOT be a full engulfing
        not_engulfing = c2['close'] <= c1['open']
        
        if not (gap_down and above_midpoint and not_engulfing):
            return []
            
        # Check for prior downtrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_downtrend = c2['close'] < sma_fast.iloc[-1] or c1['close'] < df['close'].iloc[-10]
        
        if not prior_downtrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c2['volume'] > avg_vol
        
        confidence = 0.7
        if vol_spike: confidence += 0.1
        if c2['close'] > (c1['open'] - (c1['open'] - c1['close']) * 0.3):
            confidence += 0.1 # Very deep penetration
            
        signals = [Signal(
            signal_type=SignalType.BUY,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c2['close'],
            stop_loss=min(c1['low'], c2['low']),
            market_bias=MarketBias.BULLISH,
            reasoning=f"Piercing Pattern detected. Gap down and {((c2['close']-midpoint)/(c1['open']-midpoint)*100 + 50):.0f}% penetration of prior body."
        )]
        
        return signals
