"""
Strategy: Breakout Trap (Fakeout / Liquidity Grab)
Category: support_resistance
Source: Support&resistance/Fakeout , Liquidity Grab.md

Description:
  A manipulative reversal pattern where price breaks a key level only to reverse sharply.
  - Bullish Trap: Price breaks resistance, then quickly reverses and closes below it.
  - Bearish Trap: Price breaks support, then quickly reverses and closes above it.

Logic:
  - Identify major S/R levels.
  - Detect "Sweep": Price briefly violates level.
  - Detect "Reclaim/Rejection": Price returns to previous side of level.
  - Volume expansion during sweep increases confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BreakoutTrap(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Breakout Trap"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify key S/R levels using older data
        levels_df = df.iloc[-80:-10]
        res_level = levels_df['high'].max()
        sup_level = levels_df['low'].min()
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        signals = []
        
        # Volume Spike
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = current_candle['volume'] > (avg_vol * 1.5)
        
        # 2. Bearish Breakout Trap (Fakeout of Resistance)
        # Condition: Prev or Current candle high > resistance, but current close < resistance
        was_above = (prev_candle['high'] > res_level) or (current_candle['high'] > res_level)
        is_below_now = current_candle['close'] < res_level
        
        if was_above and is_below_now and prev_candle['close'] > res_level:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.8 if vol_spike else 0.7,
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=max(prev_candle['high'], current_candle['high']),
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bearish Breakout Trap: Price failed to hold above resistance ({res_level:.2f}). Trapped buyers."
            ))
            
        # 3. Bullish Breakout Trap (Fakeout of Support)
        # Condition: Prev or Current candle low < support, but current close > support
        was_below = (prev_candle['low'] < sup_level) or (current_candle['low'] < sup_level)
        is_above_now = current_candle['close'] > sup_level
        
        if was_below and is_above_now and prev_candle['close'] < sup_level:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.8 if vol_spike else 0.7,
                timeframe=timeframe,
                entry_price=current_candle['close'],
                stop_loss=min(prev_candle['low'], current_candle['low']),
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bullish Breakout Trap: Price reclaimed support level ({sup_level:.2f}). Trapped sellers."
            ))
            
        return signals
