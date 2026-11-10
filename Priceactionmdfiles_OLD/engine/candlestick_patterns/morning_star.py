"""
Strategy: Morning Star Pattern
Category: candlestick
Source: Candlestickpatterns/Morning Star Pattern.md

Description:
  A three-candle bullish reversal pattern.
  - Candle 1: Strong bearish candle.
  - Candle 2: Small-bodied indecision candle (Star).
  - Candle 3: Strong bullish candle closing deep inside Candle 1.

Logic:
  - Must occur after a prior downtrend.
  - Candle 2 body size < 30% of Candle 1 body.
  - Candle 3 must close above the 50% midpoint of Candle 1.
  - Higher volume on Candle 3 increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class MorningStar(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Morning Star"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 30
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        if len(df) < 3:
            return []
            
        c1 = df.iloc[-3]
        c2 = df.iloc[-2]
        c3 = df.iloc[-1]
        
        # 1. Candle 1 must be Bearish
        c1_bearish = c1['close'] < c1['open']
        if not c1_bearish:
            return []
            
        # 2. Candle 2 must be small-bodied (Star)
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        if c2_body > (c1_body * 0.3) or c1_body == 0:
            return []
            
        # 3. Candle 3 must be Bullish
        c3_bullish = c3['close'] > c3['open']
        if not c3_bullish:
            return []
            
        # 4. Candle 3 must close above midpoint of C1
        c1_midpoint = (c1['open'] + c1['close']) / 2
        closes_deep = c3['close'] > c1_midpoint
        if not closes_deep:
            return []
            
        # Check for prior downtrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_downtrend = c1['close'] < sma_fast.iloc[-3] or c1['close'] < df['close'].iloc[-15]
        if not prior_downtrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c3['volume'] > avg_vol
        
        confidence = 0.75
        if vol_spike: confidence += 0.1
        if c2['close'] == c2['open']: confidence += 0.05 # Doji Star is stronger
            
        signals = [Signal(
            signal_type=SignalType.BUY,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c3['close'],
            stop_loss=min(c1['low'], c2['low'], c3['low']),
            market_bias=MarketBias.BULLISH,
            reasoning=f"Morning Star detected. 3-candle bullish reversal at potential bottom."
        )]
        
        return signals
