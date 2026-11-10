"""
Strategy: Triple Bottom Pattern
Category: price_action_pattern
Source: Price action patterns/Triple Bottom Pattern.md

Description:
  A major bullish reversal pattern with three troughs.
  - Three distinct bottoms at nearly the same level.
  - Neckline: Resistance line connecting the peaks between bottoms.

Logic:
  - Requires prior downtrend.
  - Bottoms should be within 3% of each other.
  - Signal on breakout above the neckline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class TripleBottom(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Triple Bottom"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 150
    
    def _find_swings(self, df: pd.DataFrame, window: int = 2) -> Dict[str, List[int]]:
        highs = df['high'].values
        lows = df['low'].values
        swing_highs = []
        swing_lows = []
        for i in range(window, len(df) - window):
            if all(highs[i] > highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                swing_highs.append(i)
            if all(lows[i] < lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                swing_lows.append(i)
        return {"highs": swing_highs, "lows": swing_lows}

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        swings = self._find_swings(df, window=3)
        high_indices = swings['highs']
        low_indices = swings['lows']
        
        # Need at least 3 lows and 2 highs
        if len(low_indices) < 3 or len(high_indices) < 2:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        # Look for the last three bottoms
        for i in range(len(low_indices) - 1, 1, -1):
            t3_idx = low_indices[i]
            t2_idx = low_indices[i-1]
            t1_idx = low_indices[i-2]
            
            t3_price = df['low'].iloc[t3_idx]
            t2_price = df['low'].iloc[t2_idx]
            t1_price = df['low'].iloc[t1_idx]
            
            # Bottoms should be at similar levels (within 3%)
            prices = [t1_price, t2_price, t3_price]
            if (max(prices) - min(prices)) / min(prices) > 0.03:
                continue
                
            # Look for Neckline peaks between bottoms
            peak1_opts = [h for h in high_indices if h > t1_idx and h < t2_idx]
            peak2_opts = [h for h in high_indices if h > t2_idx and h < t3_idx]
            
            if not (peak1_opts and peak2_opts):
                continue
                
            p1_idx = df['high'].loc[peak1_opts].idxmax()
            p2_idx = df['high'].loc[peak2_opts].idxmax()
            
            neckline_price = max(df['high'].loc[p1_idx], df['high'].loc[p2_idx])
            
            if (t3_idx - t1_idx) < 20: continue
            
            if current_price > neckline_price:
                signals.append(Signal(
                    signal_type=SignalType.STRONG_BUY,
                    strategy_name=self.name,
                    confidence=0.8,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=t3_price,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Triple Bottom Breakout above {neckline_price:.2f}."
                ))
                break
            elif current_price < neckline_price and current_price > t3_price:
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BULLISH,
                    reasoning="Inside Triple Bottom formation."
                ))
                break
                
        return signals
