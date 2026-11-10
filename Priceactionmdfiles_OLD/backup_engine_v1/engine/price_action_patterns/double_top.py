"""
Strategy: Double Top Pattern
Category: price_action_pattern
Source: Price action patterns/Double Top Pattern.md

Description:
  A bearish reversal pattern (M-shape).
  - Two distinct peaks (Tops) at nearly the same level.
  - Intervening trough (Neckline) between the tops.

Logic:
  - Requires prior uptrend.
  - Tops should be within 2% of each other.
  - Signal occurs on breakdown below the neckline.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class DoubleTop(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Double Top"
    
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
        
        if len(high_indices) < 2 or len(low_indices) < 1:
            return []
            
        signals = []
        current_price = df['close'].iloc[-1]
        
        for i in range(len(high_indices) - 1, 0, -1):
            h2_idx = high_indices[i]
            h2_price = df['high'].iloc[h2_idx]
            
            for j in range(i - 1, -1, -1):
                h1_idx = high_indices[j]
                h1_price = df['high'].iloc[h1_idx]
                
                # Tops within 5% (relaxed)
                if abs(h1_price - h2_price) / h1_price > 0.05: continue
                
                # Look for Neckline (Trough) between Tops
                possible_troughs = [l for l in low_indices if l > h1_idx and l < h2_idx]
                if not possible_troughs: continue
                    
                neckline_idx = df['low'].loc[possible_troughs].idxmin()
                neckline_price = df['low'].loc[neckline_idx]
                
                if (h2_idx - h1_idx) < 10: continue
                
                if current_price < neckline_price:
                    avg_vol = df['volume'].tail(20).mean()
                    vol_spike = df['volume'].iloc[-1] > avg_vol
                    
                    signals.append(Signal(
                        signal_type=SignalType.STRONG_SELL,
                        strategy_name=self.name,
                        confidence=0.85 if vol_spike else 0.75,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=h2_price,
                        market_bias=MarketBias.BEARISH,
                        reasoning=f"Double Top Breakdown below {neckline_price:.2f}."
                    ))
                    break
                elif current_price > neckline_price and current_price < h2_price:
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.6,
                        timeframe=timeframe,
                        market_bias=MarketBias.BEARISH,
                        reasoning="Inside Double Top formation."
                    ))
                    break
            if signals: break
            
        return signals
