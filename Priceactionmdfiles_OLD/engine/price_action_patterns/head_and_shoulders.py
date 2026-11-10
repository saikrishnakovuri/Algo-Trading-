"""
Strategy: Head and Shoulders Pattern
Category: price_action_pattern
Source: Price action patterns/Head and Shoulders Pattern.md

Description:
  A major bearish reversal pattern with three peaks.
  - Head: The middle and highest peak.
  - Shoulders: Two lower peaks on either side, nearly equal in height.
  - Neckline: Support line connecting the troughs between peaks.

Logic:
  - Requires prior uptrend.
  - Peaks: P1 < P2 and P3 < P2.
  - Shoulders (P1, P3) should be within 3% of each other.
  - Signal on breakdown below the neckline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class HeadAndShoulders(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Head and Shoulders"
    
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
        
        # Need at least 3 highs and 2 lows
        if len(high_indices) < 3 or len(low_indices) < 2:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        # Look for the last three peaks
        for i in range(len(high_indices) - 1, 1, -1):
            p3_idx = high_indices[i]
            p2_idx = high_indices[i-1]
            p1_idx = high_indices[i-2]
            
            p3_price = df['high'].iloc[p3_idx]
            p2_price = df['high'].iloc[p2_idx] # Head
            p1_price = df['high'].iloc[p1_idx]
            
            # Head must be highest
            if not (p2_price > p1_price and p2_price > p3_price):
                continue
                
            # Shoulders should be at similar levels (within 5% for robustness)
            if abs(p1_price - p3_price) / p1_price > 0.05:
                continue
                
            # Neckline: Find troughs between p1-p2 and p2-p3
            trough1_opts = [l for l in low_indices if l > p1_idx and l < p2_idx]
            trough2_opts = [l for l in low_indices if l > p2_idx and l < p3_idx]
            
            if not (trough1_opts and trough2_opts):
                continue
                
            t1_idx = df['low'].loc[trough1_opts].idxmin()
            t2_idx = df['low'].loc[trough2_opts].idxmin()
            
            t1_price = df['low'].loc[t1_idx]
            t2_price = df['low'].loc[t2_idx]
            
            # Neckline slope
            n_slope = (t2_price - t1_price) / (t2_idx - t1_idx)
            n_intercept = t1_price - n_slope * t1_idx
            
            # Current expected neckline support
            current_idx = len(df) - 1
            expected_neckline = n_slope * current_idx + n_intercept
            
            if current_price < expected_neckline:
                # Breakdown
                signals.append(Signal(
                    signal_type=SignalType.STRONG_SELL,
                    strategy_name=self.name,
                    confidence=0.8,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=p3_price,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Head and Shoulders Breakdown below neckline ({expected_neckline:.2f})."
                ))
                break
            elif current_price > expected_neckline and current_price < p3_price:
                # Inside right shoulder
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BEARISH,
                    reasoning="Head and Shoulders forming. Awaiting neckline breakdown."
                ))
                break
                
        return signals
