"""
Strategy: Retest Entry
Category: support_resistance
Source: Support&resistance/Retest Entry.md

Description:
  A confirmation-based entry model after a breakout.
  - Signal occurs when price returns to a broken level and rejects it.

Logic:
  - Detect prior clear breakout of S/R level.
  - Detect return to the level (Pullback).
  - Rejection: Bullish rejection at old Resistance (now Support) or Bearish at old Support (now Resistance).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class RetestEntry(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Retest Entry"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify older S/R levels
        levels_df = df.iloc[-100:-30]
        res_level = levels_df['high'].max()
        sup_level = levels_df['low'].min()
        
        current_candle = df.iloc[-1]
        
        signals = []
        
        # 2. Bullish Retest (Old Resistance -> New Support)
        # Look for a breakout in recent history (idx -30 to -5)
        breakout_idx = -1
        for i in range(len(df) - 40, len(df) - 5):
            if df['close'].iloc[i] > res_level and df['close'].iloc[i-1] <= res_level:
                breakout_idx = i
                break
                
        if breakout_idx != -1:
            # Current price is retesting
            # Condition: Current low near res_level AND close > res_level
            if current_candle['low'] <= res_level * 1.01 and current_candle['close'] > res_level:
                # Bullish Rejection wick or body
                lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
                is_rejection = lower_wick > (current_candle['high'] - current_candle['low']) * 0.4 or current_candle['close'] > current_candle['open']
                
                if is_rejection:
                    signals.append(Signal(
                        signal_type=SignalType.BUY,
                        strategy_name=self.name,
                        confidence=0.8,
                        timeframe=timeframe,
                        entry_price=current_candle['close'],
                        stop_loss=current_candle['low'] * 0.998,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Bullish Retest: Price rejected old resistance ({res_level:.2f}) which is now support."
                    ))

        # 3. Bearish Retest (Old Support -> New Resistance)
        breakdown_idx = -1
        for i in range(len(df) - 40, len(df) - 5):
            if df['close'].iloc[i] < sup_level and df['close'].iloc[i-1] >= sup_level:
                breakdown_idx = i
                break
                
        if breakdown_idx != -1:
            if current_candle['high'] >= sup_level * 0.99 and current_candle['close'] < sup_level:
                upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
                is_rejection = upper_wick > (current_candle['high'] - current_candle['low']) * 0.4 or current_candle['close'] < current_candle['open']
                
                if is_rejection:
                    signals.append(Signal(
                        signal_type=SignalType.SELL,
                        strategy_name=self.name,
                        confidence=0.8,
                        timeframe=timeframe,
                        entry_price=current_candle['close'],
                        stop_loss=current_candle['high'] * 1.002,
                        market_bias=MarketBias.BEARISH,
                        reasoning=f"Bearish Retest: Price rejected old support ({sup_level:.2f}) which is now resistance."
                    ))
                    
        return signals
