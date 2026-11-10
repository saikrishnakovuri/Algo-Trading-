"""
Strategy: Double Bottom Pattern
Category: price_action_pattern
Source: Price action patterns/Double Bottom Pattern.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class DoubleBottom(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Double Bottom"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 100
    
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
            
        swings = self._find_swings(df, window=2)
        high_indices = swings['highs']
        low_indices = swings['lows']
        
        if len(low_indices) < 2 or len(high_indices) < 1:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        for i in range(len(low_indices) - 1, 0, -1):
            l2_idx = low_indices[i]
            l2_price = df['low'].iloc[l2_idx]
            
            for j in range(i - 1, -1, -1):
                l1_idx = low_indices[j]
                l1_price = df['low'].iloc[l1_idx]
                
                if abs(l1_price - l2_price) / l1_price > 0.05: continue
                
                possible_peaks = [h for h in high_indices if h > l1_idx and h < l2_idx]
                if not possible_peaks: continue
                    
                neckline_idx = df['high'].loc[possible_peaks].idxmax()
                neckline_price = df['high'].loc[neckline_idx]
                
                if (l2_idx - l1_idx) < 10: continue
                
                if current_price > neckline_price:
                    signals.append(Signal(
                        signal_type=SignalType.STRONG_BUY,
                        strategy_name=self.name,
                        confidence=0.8,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=l2_price,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Double Bottom Breakout above {neckline_price:.2f}."
                    ))
                    break
                elif current_price < neckline_price and current_price > l2_price:
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.6,
                        timeframe=timeframe,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Inside Double Bottom formation."
                    ))
                    break
            if signals: break
            
        return signals
