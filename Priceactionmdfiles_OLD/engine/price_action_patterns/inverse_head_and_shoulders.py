"""
Strategy: Inverse Head and Shoulders Pattern
Category: price_action_pattern
Source: Price action patterns/Inverse Head and Shoulders Pattern.md

Description:
  A major bullish reversal pattern with three troughs.
  - Head: The middle and lowest trough.
  - Shoulders: Two higher troughs on either side, nearly equal in depth.
  - Neckline: Resistance line connecting the peaks between troughs.

Logic:
  - Requires prior downtrend.
  - Troughs: T1 > T2 and T3 > T2.
  - Shoulders (T1, T3) should be within 5% of each other.
  - Signal on breakout above the neckline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class InverseHeadAndShoulders(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Inverse Head and Shoulders"
    
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
        
        if len(low_indices) < 3 or len(high_indices) < 2:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        for i in range(len(low_indices) - 1, 1, -1):
            t3_idx = low_indices[i]
            t2_idx = low_indices[i-1] # Head
            t1_idx = low_indices[i-2]
            
            t3_price = df['low'].iloc[t3_idx]
            t2_price = df['low'].iloc[t2_idx]
            t1_price = df['low'].iloc[t1_idx]
            
            if not (t2_price < t1_price and t2_price < t3_price):
                continue
                
            if abs(t1_price - t3_price) / t1_price > 0.05:
                continue
                
            peak1_opts = [h for h in high_indices if h > t1_idx and h < t2_idx]
            peak2_opts = [h for h in high_indices if h > t2_idx and h < t3_idx]
            
            if not (peak1_opts and peak2_opts):
                continue
                
            p1_idx = df['high'].loc[peak1_opts].idxmax()
            p2_idx = df['high'].loc[peak2_opts].idxmax()
            
            p1_price = df['high'].loc[p1_idx]
            p2_price = df['high'].loc[p2_idx]
            
            n_slope = (p2_price - p1_price) / (p2_idx - p1_idx)
            n_intercept = p1_price - n_slope * p1_idx
            
            current_idx = len(df) - 1
            expected_neckline = n_slope * current_idx + n_intercept
            
            if current_price > expected_neckline:
                avg_vol = df['volume'].tail(20).mean()
                vol_spike = df['volume'].iloc[-1] > avg_vol
                
                signals.append(Signal(
                    signal_type=SignalType.STRONG_BUY,
                    strategy_name=self.name,
                    confidence=0.85 if vol_spike else 0.75,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=t3_price,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Inverse Head and Shoulders Breakout above neckline ({expected_neckline:.2f})."
                ))
                break
            elif current_price < expected_neckline and current_price > t3_price:
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BULLISH,
                    reasoning="Inverse Head and Shoulders forming. Awaiting breakout."
                ))
                break
                
        return signals
