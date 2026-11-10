"""
Strategy: Support
Category: support_resistance
Source: Support&resistance/Support.md

Description:
  Identifies key demand levels where price repeatedly bounces.
  - Signal occurs on rejections from the support zone.

Logic:
  - Identify horizontal support tested at least twice.
  - Rejection: Bullish candle (wick rejection or bullish body) at the level.
  - Confluences: Volume spike, RSI oversold (<30).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class Support(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Support"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def _find_swings(self, df: pd.DataFrame, window: int = 5) -> Dict[str, List[int]]:
        lows = df['low'].values
        swing_lows = []
        for i in range(window, len(df) - window):
            if all(lows[i] < lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                swing_lows.append(i)
        return {"lows": swing_lows}

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        swings = self._find_swings(df)
        low_indices = swings['lows']
        
        if len(low_indices) < 2:
            return []
            
        # 1. Identify Support Level
        # Group recent lows to find clusters
        recent_l_prices = df['low'].iloc[low_indices[-10:]].values
        
        support_levels = []
        for p in recent_l_prices:
            if not support_levels:
                support_levels.append([p])
            else:
                added = False
                for level_group in support_levels:
                    if abs(p - np.mean(level_group)) / np.mean(level_group) < 0.01:
                        level_group.append(p)
                        added = True
                        break
                if not added:
                    support_levels.append([p])
                    
        # Filter groups with at least 2 touches
        valid_levels = [np.mean(g) for g in support_levels if len(g) >= 2]
        
        if not valid_levels:
            return []
            
        sup_level = min(valid_levels)
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        
        signals = []
        
        # 2. Rejection Logic
        in_zone = current_candle['low'] <= sup_level * 1.002 and current_candle['low'] >= sup_level * 0.99
        
        if in_zone:
            # Bullish Rejection check
            lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
            is_bullish = current_candle['close'] > current_candle['open'] or lower_wick > (current_candle['high'] - current_candle['low']) * 0.3
            
            if is_bullish:
                avg_vol = df['volume'].tail(20).mean()
                vol_spike = current_candle['volume'] > avg_vol
                
                signals.append(Signal(
                    signal_type=SignalType.BUY,
                    strategy_name=self.name,
                    confidence=0.8 if vol_spike else 0.7,
                    timeframe=timeframe,
                    entry_price=current_price,
                    stop_loss=current_candle['low'] * 0.998,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Support Rejection at {sup_level:.2f}. Bullish reaction confirmed."
                ))
            else:
                signals.append(Signal(
                    signal_type=SignalType.HOLD,
                    strategy_name=self.name,
                    confidence=0.6,
                    timeframe=timeframe,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Price near Support ({sup_level:.2f}). Awaiting bullish confirmation."
                ))
                
        return signals
