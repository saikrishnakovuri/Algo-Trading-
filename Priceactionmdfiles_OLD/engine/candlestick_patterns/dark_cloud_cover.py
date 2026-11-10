"""
Strategy: Dark Cloud Cover Pattern
Category: candlestick
Source: Candlestickpatterns/Dark Cloud Cover Pattern.md

Description:
  A two-candle bearish reversal pattern.
  - Candle 1: Strong bullish candle.
  - Candle 2: Bearish candle that opens above Candle 1's close and closes below its midpoint.

Logic:
  - Must occur after a prior uptrend.
  - Candle 2 must close deep into Candle 1's body (at least below 50%).
  - Higher volume on Candle 2 increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class DarkCloudCover(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Dark Cloud Cover"
    
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
        
        # Candle 1 must be strongly Bullish
        c1_bullish = c1['close'] > c1['open']
        # Candle 2 must be Bearish
        c2_bearish = c2['close'] < c2['open']
        
        if not (c1_bullish and c2_bearish):
            return []
            
        # 1. Gap up: C2 open > C1 close
        gap_up = c2['open'] > c1['close']
        
        # 2. Closes below midpoint: C2 close < (C1 open + C1 close) / 2
        midpoint = (c1['open'] + c1['close']) / 2
        below_midpoint = c2['close'] < midpoint
        
        # 3. Optional: Should NOT be a full engulfing (standard definition)
        # but the MD says "does not need to", implying it can.
        # However, to keep it distinct from Bearish Engulfing:
        not_engulfing = c2['close'] >= c1['open']
        
        if not (gap_up and below_midpoint and not_engulfing):
            return []
            
        # Check for prior uptrend
        sma_fast = df['close'].rolling(window=10).mean()
        prior_uptrend = c2['close'] > sma_fast.iloc[-1] or c1['close'] > df['close'].iloc[-10]
        
        if not prior_uptrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c2['volume'] > avg_vol
        
        confidence = 0.7
        if vol_spike: confidence += 0.1
        if c2['close'] < (c1['open'] + (c1['close'] - c1['open']) * 0.3):
            confidence += 0.1 # Very deep penetration
            
        signals = [Signal(
            signal_type=SignalType.SELL,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c2['close'],
            stop_loss=max(c1['high'], c2['high']),
            market_bias=MarketBias.BEARISH,
            reasoning=f"Dark Cloud Cover detected. Gap up and {((midpoint-c2['close'])/(midpoint-c1['open'])*100 + 50):.0f}% penetration of prior body."
        )]
        
        return signals
