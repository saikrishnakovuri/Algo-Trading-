"""
Strategy: Evening Star Pattern
Category: candlestick
Source: Candlestickpatterns/Evening Star Pattern.md

Description:
  A three-candle bearish reversal pattern.
  - Candle 1: Strong bullish candle.
  - Candle 2: Small-bodied indecision candle (Star).
  - Candle 3: Strong bearish candle closing deep inside Candle 1.

Logic:
  - Must occur after a prior uptrend.
  - Candle 2 body size < 30% of Candle 1 body.
  - Candle 3 must close below the 50% midpoint of Candle 1.
  - Higher volume on Candle 3 increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class EveningStar(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Evening Star"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 30
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # Need at least 3 candles
        if len(df) < 3:
            return []
            
        c1 = df.iloc[-3]
        c2 = df.iloc[-2]
        c3 = df.iloc[-1]
        
        # 1. Candle 1 must be Bullish
        c1_bullish = c1['close'] > c1['open']
        if not c1_bullish:
            return []
            
        # 2. Candle 2 must be small-bodied (Star)
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        if c2_body > (c1_body * 0.3) or c1_body == 0:
            return []
            
        # 3. Candle 3 must be Bearish
        c3_bearish = c3['close'] < c3['open']
        if not c3_bearish:
            return []
            
        # 4. Candle 3 must close below midpoint of C1
        c1_midpoint = (c1['open'] + c1['close']) / 2
        closes_deep = c3['close'] < c1_midpoint
        if not closes_deep:
            return []
            
        # Check for prior uptrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_uptrend = c1['close'] > sma_fast.iloc[-3] or c1['close'] > df['close'].iloc[-15]
        if not prior_uptrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c3['volume'] > avg_vol
        
        confidence = 0.75
        if vol_spike: confidence += 0.1
        if c2['close'] == c2['open']: confidence += 0.05 # Doji Star is stronger
            
        signals = [Signal(
            signal_type=SignalType.SELL,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c3['close'],
            stop_loss=max(c1['high'], c2['high'], c3['high']),
            market_bias=MarketBias.BEARISH,
            reasoning=f"Evening Star detected. 3-candle bearish reversal at potential peak."
        )]
        
        return signals
