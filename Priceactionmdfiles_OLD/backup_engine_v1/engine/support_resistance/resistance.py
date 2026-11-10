"""
Strategy: Resistance
Category: support_resistance
Source: Support&resistance/Resistance.md

Description:
  Identifies key supply levels where price repeatedly rejects.
  - Signal occurs on rejections from the resistance zone.

Logic:
  - Identify horizontal resistance tested at least twice.
  - Rejection: Bearish candle (wick rejection or bearish body) at the level.
  - Confluences: Volume spike, RSI overbought (>70).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class Resistance(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Resistance"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def _find_swings(self, df: pd.DataFrame, window: int = 5) -> Dict[str, List[int]]:
        highs = df['high'].values
        swing_highs = []
        for i in range(window, len(df) - window):
            if all(highs[i] > highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                swing_highs.append(i)
        return {"highs": swing_highs}

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        swings = self._find_swings(df)
        high_indices = swings['highs']
        
        if len(high_indices) < 2:
            return []
            
        # 1. Identify Resistance Level
        # Group recent highs to find clusters
        recent_h_prices = df['high'].iloc[high_indices[-10:]].values
        
        # Simple grouping by proximity (within 0.5%)
        resistance_levels = []
        for p in recent_h_prices:
            if not resistance_levels:
                resistance_levels.append([p])
            else:
                added = False
                for level_group in resistance_levels:
                    if abs(p - np.mean(level_group)) / np.mean(level_group) < 0.01:
                        level_group.append(p)
                        added = True
                        break
                if not added:
                    resistance_levels.append([p])
                    
        # Filter groups with at least 2 touches
        valid_levels = [np.mean(g) for g in resistance_levels if len(g) >= 2]
        
        if not valid_levels:
            return []
            
        res_level = max(valid_levels)
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        
        signals = []
        
        # 2. Rejection Logic
        # Price is near or just touched resistance
        in_zone = current_candle['high'] >= res_level * 0.998 and current_candle['high'] <= res_level * 1.01
        
        if in_zone:
            # Bearish Rejection check (wick or bearish body)
            upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
            is_bearish = current_candle['close'] < current_candle['open'] or upper_wick > (current_candle['high'] - current_candle['low']) * 0.3
            
            if is_bearish:
                avg_vol = df['volume'].tail(20).mean()
                vol_spike = current_candle['volume'] > avg_vol
                
                signals.append(Signal(
                    signal_type=SignalType.SELL,
                    strategy_name=self.name,
                    confidence=0.8 if vol_spike else 0.7,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=current_candle['high'] * 1.002,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Resistance Rejection at {res_level:.2f}. Bearish reaction confirmed."
                ))
            else:
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Price near Resistance ({res_level:.2f}). Awaiting bearish confirmation."
                ))
                
        return signals
