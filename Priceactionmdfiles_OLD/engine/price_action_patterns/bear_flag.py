"""
Strategy: Bear Flag Pattern
Category: price_action_pattern
Source: Price action patterns/Bear Flag Pattern.md

Description:
  A bearish continuation pattern.
  - Flagpole: A sharp, impulsive bearish move.
  - Flag: A tight, upward-sloping consolidation channel.

Logic:
  - Requires a strong initial drop (high momentum).
  - Consolidation should be weak and retracement < 50% of the flagpole.
  - Signal occurs on breakdown below the flag support line.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class BearFlag(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Bear Flag"
    
    @property
    def category(self) -> str:
        return "price_action_pattern"
    
    @property
    def required_candles(self) -> int:
        return 50
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify Flagpole (Impulsive Drop)
        # Look back for a sharp drop in the last 20-40 candles
        # We'll use a sliding window to find the max drop over 10 candles
        window = 10
        price_diff = df['close'].diff(periods=window)
        min_diff_idx = price_diff.tail(30).idxmin()
        
        if pd.isna(min_diff_idx): return []
        
        drop_magnitude = -price_diff.loc[min_diff_idx]
        flagpole_start_idx = df.index.get_loc(min_diff_idx) - window
        flagpole_end_idx = df.index.get_loc(min_diff_idx)
        
        # Threshold: Drop must be significant (> 2.0x average candle size)
        avg_candle = (df['high'] - df['low']).tail(50).mean()
        if drop_magnitude < (avg_candle * 5.0):
            return []
            
        # 2. Identify Flag (Consolidation)
        # Consolidation is from flagpole_end_idx to now
        flag_df = df.iloc[flagpole_end_idx:]
        if len(flag_df) < 5 or len(flag_df) > 30:
            return []
            
        # Check retracement depth
        max_rebound = flag_df['high'].max() - df['close'].iloc[flagpole_end_idx]
        if max_rebound > (drop_magnitude * 0.5):
            return [] # Too deep
            
        # 3. Flag Structure (Rising Trendline)
        # Fit trendline to lows of the flag
        flag_lows = flag_df['low'].values
        x_flag = np.arange(len(flag_lows))
        slope, intercept = np.polyfit(x_flag, flag_lows, 1)
        
        # Flag should be neutral or slightly upward sloping
        if slope < -0.01: # Significant downward slope means it's just continuation, not a flag
            return []
            
        # 4. Breakdown Logic
        current_idx = len(flag_df) - 1
        expected_support = slope * current_idx + intercept
        current_price = df['close'].iloc[-1]
        
        signals = []
        
        if current_price < expected_support:
            # Volume confirmation
            avg_vol = df['volume'].tail(20).mean()
            vol_spike = df['volume'].iloc[-1] > avg_vol
            
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.8 if vol_spike else 0.7,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=flag_df['high'].max(),
                market_bias=MarketBias.BEARISH,
                reasoning=f"Bear Flag Breakdown. Flagpole magnitude: {drop_magnitude:.2f}."
            ))
        else:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=0.6,
                timeframe=timeframe,
                market_bias=MarketBias.BEARISH,
                reasoning="Potential Bear Flag forming. Awaiting breakdown."
            ))
            
        return signals
