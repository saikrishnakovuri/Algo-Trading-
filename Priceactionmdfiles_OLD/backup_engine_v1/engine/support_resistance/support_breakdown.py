"""
Strategy: Support Breakdown
Category: support_resistance
Source: Support&resistance/Support Breakdown.md

Description:
  Bearish breakdown specifically below a key support level.
  - Signal occurs when price breaks and holds below support.

Logic:
  - Identify major support zone.
  - Requires strong bearish candle body and high volume.
  - RSI < 40 confirms momentum.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class SupportBreakdown(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Support Breakdown"
    
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
            
        # 1. Identify Support Level
        levels_df = df.iloc[-100:-5]
        sup_level = levels_df['low'].min()
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        signals = []
        
        # 2. Breakdown Conditions
        is_breakdown = current_candle['close'] < sup_level and prev_candle['close'] >= sup_level
        
        if is_breakdown:
            # Body check
            avg_body = (df['close'] - df['open']).abs().tail(20).mean()
            current_body = abs(current_candle['close'] - current_candle['open'])
            
            # Volume check
            avg_vol = df['volume'].tail(20).mean()
            vol_spike = current_candle['volume'] > (avg_vol * 1.5)
            
            # RSI momentum check
            rsi = self._calculate_rsi(df).iloc[-1]
            
            if current_body > avg_body:
                confidence = 0.7
                if vol_spike: confidence += 0.1
                if rsi < 40: confidence += 0.1
                
                signals.append(Signal(
                    signal_type=SignalType.SELL,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=sup_level * 1.005,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Support Breakdown below {sup_level:.2f}. RSI: {rsi:.1f}. {'Volume expansion confirmed.' if vol_spike else ''}"
                ))
                
        return signals
