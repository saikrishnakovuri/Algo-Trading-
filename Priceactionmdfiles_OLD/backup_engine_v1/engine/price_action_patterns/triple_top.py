"""
Strategy: Triple Top Pattern
Category: price_action_pattern
Source: Price action patterns/Triple Top Pattern.md

Description:
  A major bearish reversal pattern with three peaks.
  - Three distinct tops at nearly the same level.
  - Neckline: Support line connecting the troughs between tops.

Logic:
  - Requires prior uptrend.
  - Tops should be within 3% of each other.
  - Signal on breakdown below the neckline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class TripleTop(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Triple Top"
    
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
        
        if len(high_indices) < 3 or len(low_indices) < 2:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        # Look for the last three tops
        for i in range(len(high_indices) - 1, 1, -1):
            p3_idx = high_indices[i]
            p2_idx = high_indices[i-1]
            p1_idx = high_indices[i-2]
            
            p3_price = df['high'].iloc[p3_idx]
            p2_price = df['high'].iloc[p2_idx]
            p1_price = df['high'].iloc[p1_idx]
            
            # Tops within 3%
            prices = [p1_price, p2_price, p3_price]
            if (max(prices) - min(prices)) / min(prices) > 0.03:
                continue
                
            # Look for Neckline troughs between tops
            t1_opts = [l for l in low_indices if l > p1_idx and l < p2_idx]
            t2_opts = [l for l in low_indices if l > p2_idx and l < p3_idx]
            
            if not (t1_opts and t2_opts):
                continue
                
            l1_idx = df['low'].loc[t1_opts].idxmin()
            l2_idx = df['low'].loc[t2_opts].idxmin()
            
            neckline_price = min(df['low'].loc[l1_idx], df['low'].loc[l2_idx])
            
            if (p3_idx - p1_idx) < 20: continue
            
            if current_price < neckline_price:
                avg_vol = df['volume'].tail(20).mean()
                vol_spike = df['volume'].iloc[-1] > avg_vol
                
                signals.append(Signal(
                    signal_type=SignalType.STRONG_SELL,
                    strategy_name=self.name,
                    confidence=0.8,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=p3_price,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Triple Top Breakdown below {neckline_price:.2f}."
                ))
                break
            elif current_price > neckline_price and current_price < p3_price:
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BEARISH,
                    reasoning="Inside Triple Top formation."
                ))
                break
                
        return signals
