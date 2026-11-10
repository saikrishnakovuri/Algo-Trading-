"""
Strategy: Cup and Handle Pattern
Category: price_action_pattern
Source: Price action patterns/Cup and Handle Pattern.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class CupAndHandle(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Cup and Handle"
    
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
            lip2_idx = high_indices[i]
            lip2_price = df['high'].iloc[lip2_idx]
            
            for j in range(i - 1, -1, -1):
                lip1_idx = high_indices[j]
                lip1_price = df['high'].iloc[lip1_idx]
                
                # Relaxed checks
                if abs(lip1_price - lip2_price) / lip1_price > 0.05: continue
                if (lip2_idx - lip1_idx) < 10: continue
                
                possible_bottoms = [l for l in low_indices if l > lip1_idx and l < lip2_idx]
                if not possible_bottoms: continue
                    
                bottom_idx = df['low'].loc[possible_bottoms].idxmin()
                bottom_price = df['low'].loc[bottom_idx]
                cup_depth = lip1_price - bottom_price
                if cup_depth <= 0: continue
                
                # 2. Identify Handle
                if lip2_idx >= len(df) - 2: continue
                    
                handle_df = df.iloc[lip2_idx:]
                handle_low = handle_df['low'].min()
                handle_retracement = lip2_price - handle_low
                if handle_retracement > (cup_depth * 0.6): continue
                    
                resistance = max(lip1_price, lip2_price)
                if current_price > resistance:
                    signals.append(Signal(
                        signal_type=SignalType.STRONG_BUY,
                        strategy_name=self.name,
                        confidence=0.8,
                        timeframe=timeframe,
                        entry_price=current_price,
                        stop_loss=handle_low,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Cup and Handle Breakout above {resistance:.2f}."
                    ))
                    break
                elif current_price < resistance and current_price > handle_low:
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.6,
                        timeframe=timeframe,
                        market_bias=MarketBias.BULLISH,
                        reasoning=f"Inside Cup and Handle structure."
                    ))
                    break
            if signals: break
            
        return signals
