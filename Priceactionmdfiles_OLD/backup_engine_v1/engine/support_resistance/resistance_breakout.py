"""
Strategy: Resistance Breakout
Category: support_resistance
Source: Support&resistance/Resistance Breakout.md

Description:
  Bullish breakout specifically above a key resistance level.
  - Signal occurs when price breaks and holds above resistance.

Logic:
  - Identify major resistance zone.
  - Requires strong bullish candle body and high volume.
  - RSI > 60 confirms momentum.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class ResistanceBreakout(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Resistance Breakout"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Resistance Level
        # Use older data to find the ceiling
        levels_df = df.iloc[-80:-5]
        res_level = levels_df['high'].max()
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        signals = []
        
        # 2. Breakout Conditions
        # Price closes above resistance
        is_breakout = current_candle['close'] > res_level and prev_candle['close'] <= res_level
        
        if is_breakout:
            # Body check
            avg_body = (df['close'] - df['open']).abs().tail(20).mean()
            current_body = current_candle['close'] - current_candle['open']
            
            # Volume check
            avg_vol = df['volume'].tail(20).mean()
            vol_spike = current_candle['volume'] > (avg_vol * 1.5)
            
            # RSI momentum check
            rsi = self._calculate_rsi(df).iloc[-1]
            
            if current_body > avg_body:
                confidence = 0.7
                if vol_spike: confidence += 0.1
                if rsi > 60: confidence += 0.1
                
                signals.append(Signal(
                    signal_type=SignalType.BUY,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=res_level * 0.995,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Resistance Breakout above {res_level:.2f}. RSI: {rsi:.1f}. {'Volume expansion confirmed.' if vol_spike else ''}"
                ))
                
        return signals
