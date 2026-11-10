"""
Strategy: Liquidity Grab (Fakeout)
Category: support_resistance
Source: Support&resistance/Fakeout , Liquidity Grab.md

Description:
  Identifies institutional stop hunts and liquidity sweeps.
  - Bullish Grab: Price sweeps below support and reverses upward.
  - Bearish Grab: Price sweeps above resistance and reverses downward.

Logic:
  - Detect "Sweep": Price briefly penetrates major S/R.
  - Detect "Rejection": Price quickly returns to the previous side.
  - Strong wick and volume spike increase confidence.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class LiquidityGrab(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Liquidity Grab"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify major S/R levels
        levels_df = df.iloc[-80:-5]
        res_level = levels_df['high'].max()
        sup_level = levels_df['low'].min()
        
        current_candle = df.iloc[-1]
        
        signals = []
        
        # Volume Spike
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = current_candle['volume'] > (avg_vol * 1.5)
        
        total_range = current_candle['high'] - current_candle['low']
        if total_range == 0: return []
        
        # 2. Bearish Liquidity Grab (Resistance Sweep)
        # Price breaks high, but closes below resistance
        if current_candle['high'] > res_level and current_candle['close'] < res_level:
            # Rejection Wick
            upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
            if upper_wick > (total_range * 0.4):
                signals.append(Signal(
                    signal_type=SignalType.STRONG_SELL,
                    strategy_name=self.name,
                    confidence=0.85 if vol_spike else 0.75,
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=current_candle['high'],
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Bearish Liquidity Grab: Price swept resistance ({res_level:.2f}) and rejected sharply."
                ))
                
        # 3. Bullish Liquidity Grab (Support Sweep)
        # Price breaks low, but closes above support
        if current_candle['low'] < sup_level and current_candle['close'] > sup_level:
            lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
            if lower_wick > (total_range * 0.4):
                signals.append(Signal(
                    signal_type=SignalType.STRONG_BUY,
                    strategy_name=self.name,
                    confidence=0.85 if vol_spike else 0.75,
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=current_candle['low'],
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Bullish Liquidity Grab: Price swept support ({sup_level:.2f}) and rejected sharply."
                ))
                
        return signals
