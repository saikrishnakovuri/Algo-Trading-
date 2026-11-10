"""
Strategy: Breakout -> Retest -> Continuation
Category: support_resistance
Source: Support&resistance/Breakout → Retest → Continuation.md

Description:
  A professional three-phase entry model.
  1. Breakout: Price aggressively breaks a key level.
  2. Retest: Price returns to the broken level and rejects it.
  3. Continuation: Trend resumes with strong momentum.

Logic:
  - Identify major S/R level.
  - Detect breakout (Close above/below level).
  - Detect retest (Low/High near broken level).
  - Signal on continuation (breaking the breakout candle's extreme).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BreakoutRetestContinuation(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Breakout-Retest-Continuation"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify S/R Level using recent peaks/troughs
        # We'll use rolling max/min to find consistent levels
        window = 20
        rolling_max = df['high'].rolling(window=window).max()
        rolling_min = df['low'].rolling(window=window).min()
        
        # Look back 50 candles for a level
        levels_df = df.iloc[-80:-20] # Older data to find level
        res_level = levels_df['high'].max()
        sup_level = levels_df['low'].min()
        
        signals = []
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        
        # 2. Bullish Breakout -> Retest -> Continuation
        # Look for breakout in the last 20 candles
        breakout_idx = -1
        for i in range(len(df) - 30, len(df) - 5):
            if df['close'].iloc[i] > res_level and df['close'].iloc[i-1] <= res_level:
                breakout_idx = i
                break
                
        if breakout_idx != -1:
            # Check for retest after breakout
            retest_df = df.iloc[breakout_idx+1:]
            retested = (retest_df['low'] <= res_level * 1.01).any() # Within 1% of level
            held = (retest_df['close'] >= res_level * 0.995).all() # Didn't crash back deep
            
            if retested and held:
                # Continuation: Breaking the breakout high
                breakout_high = df['high'].iloc[breakout_idx]
                if current_price > breakout_high:
                    signals.append(Signal(
                        signal_type=SignalType.STRONG_BUY,
                        strategy_name=self.name,
                        confidence=0.85,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=res_level * 0.99,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Bullish B-R-C: Confirmed breakout above {res_level:.2f} with successful retest."
                    ))

        # 3. Bearish Breakdown -> Retest -> Continuation
        breakdown_idx = -1
        for i in range(len(df) - 30, len(df) - 5):
            if df['close'].iloc[i] < sup_level and df['close'].iloc[i-1] >= sup_level:
                breakdown_idx = i
                break
                
        if breakdown_idx != -1:
            retest_df = df.iloc[breakdown_idx+1:]
            retested = (retest_df['high'] >= sup_level * 0.99).any()
            held = (retest_df['close'] <= sup_level * 1.005).all()
            
            if retested and held:
                breakdown_low = df['low'].iloc[breakdown_idx]
                if current_price < breakdown_low:
                    signals.append(Signal(
                        signal_type=SignalType.STRONG_SELL,
                        strategy_name=self.name,
                        confidence=0.85,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=sup_level * 1.01,
                        market_bias=MarketBias.BEARISH,
                        reasoning=f"Bearish B-R-C: Confirmed breakdown below {sup_level:.2f} with successful retest."
                    ))
                    
        return signals
