"""
Strategy: Bull Flag Pattern
Category: price_action_pattern
Source: Price action patterns/Bull Flag Pattern.md

Description:
  A bullish continuation pattern.
  - Flagpole: A sharp, impulsive bullish move.
  - Flag: A tight, downward-sloping consolidation channel.

Logic:
  - Requires a strong initial rise (high momentum).
  - Consolidation should be weak and retracement < 50% of the flagpole.
  - Signal occurs on breakout above the flag resistance line.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BullFlag(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Bull Flag"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 50
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Flagpole (Impulsive Rise)
        window = 10
        price_diff = df['close'].diff(periods=window)
        max_diff_idx = price_diff.tail(30).idxmax()
        
        if pd.isna(max_diff_idx): return []
        
        rise_magnitude = price_diff.loc[max_diff_idx]
        flagpole_start_idx = df.index.get_loc(max_diff_idx) - window
        flagpole_end_idx = df.index.get_loc(max_diff_idx)
        
        avg_candle = (df['high'] - df['low']).tail(50).mean()
        if rise_magnitude < (avg_candle * 5.0):
            return []
            
        # 2. Identify Flag (Consolidation)
        flag_df = df.iloc[flagpole_end_idx:]
        if len(flag_df) < 5 or len(flag_df) > 30:
            return []
            
        # Check retracement depth
        max_pullback = df['close'].iloc[flagpole_end_idx] - flag_df['low'].min()
        if max_pullback > (rise_magnitude * 0.5):
            return []
            
        # 3. Flag Structure (Descending Trendline for Resistance)
        flag_highs = flag_df['high'].values
        x_flag = np.arange(len(flag_highs))
        slope, intercept = np.polyfit(x_flag, flag_highs, 1)
        
        # Flag should be neutral or slightly downward sloping
        if slope > 0.01:
            return []
            
        # 4. Breakout Logic
        current_idx = len(flag_df) - 1
        expected_resistance = slope * current_idx + intercept
        current_price = df['close'].iloc[-1]
        
        signals = []
        
        if current_price > expected_resistance:
            avg_vol = df['volume'].tail(20).mean()
            vol_spike = df['volume'].iloc[-1] > avg_vol
            
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.8 if vol_spike else 0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=flag_df['low'].min(),
                market_bias=MarketBias.BULLISH,
                reasoning=f"Bull Flag Breakout. Flagpole magnitude: {rise_magnitude:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BULLISH,
                reasoning="Potential Bull Flag forming. Awaiting breakout."
            ))
            
        return signals
