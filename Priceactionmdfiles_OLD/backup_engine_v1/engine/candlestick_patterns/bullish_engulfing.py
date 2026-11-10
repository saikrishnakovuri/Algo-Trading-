"""
Strategy: Bullish Engulfing Pattern
Category: candlestick
Source: Candlestickpatterns/Bullish Engulfing Pattern.md

Description:
  A two-candle bullish reversal pattern.
  - Candle 1: Bearish candle.
  - Candle 2: Larger bullish candle that completely engulfs the body of Candle 1.

Logic:
  - Must occur after a prior downtrend.
  - Bullish candle body must be significantly larger than the prior bearish body.
  - High volume on the engulfing candle increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BullishEngulfing(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Bullish Engulfing"
    
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
        
        # Candle 1 must be Bearish
        c1_bearish = c1['close'] < c1['open']
        # Candle 2 must be Bullish
        c2_bullish = c2['close'] > c2['open']
        
        if not (c1_bearish and c2_bullish):
            return []
            
        # Body Engulfing Logic
        # C2 body [open, close] must engulf C1 body [close, open]
        engulfs = (c2['open'] <= c1['close']) and (c2['close'] > c1['open'])
        
        if not engulfs:
            return []
            
        # Check for prior downtrend (simple 10-period SMA check)
        sma_fast = df['close'].rolling(window=10).mean()
        prior_downtrend = c2['close'] < sma_fast.iloc[-1] or c1['close'] < df['close'].iloc[-10]
        
        if not prior_downtrend:
            return []
            
        # Confluences
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = c2['volume'] > avg_vol
        
        # Confidence calculation
        confidence = 0.7
        if vol_spike: confidence += 0.1
        if (c2['close'] - c2['open']) > (c1['open'] - c1['close']) * 2:
            confidence += 0.1 # Strong expansion
            
        signals = [Signal(
            signal_type=SignalType.BUY,
            strategy_name=self.name,
            confidence=min(confidence, 1.0),
            timeframe=timeframe,
            entry_price=c2['close'],
            stop_loss=min(c1['low'], c2['low']),
            market_bias=MarketBias.BULLISH,
            reasoning=f"Bullish Engulfing detected after downtrend. "
                      f"Body size expansion: {(c2['close']-c2['open'])/(c1['open']-c1['close']):.1f}x. "
                      f"{'High volume confirmation.' if vol_spike else ''}"
        )]
        
        return signals
