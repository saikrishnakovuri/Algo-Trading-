"""
Strategy: Breakout
Category: support_resistance
Source: Support&resistance/Breakout.md

Description:
  Price aggressively breaks a key support or resistance level.
  - Bullish Breakout: Close above Resistance.
  - Bearish Breakdown: Close below Support.

Logic:
  - Requires a strong candle body.
  - Requires high volume expansion.
  - Signals sudden buyer/seller imbalance.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class Breakout(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Breakout"
    
    @property
    def category(self) -> str:
        return "support_resistance"
    
    @property
    def required_candles(self) -> int:
        return 100

    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        # 1. Identify key levels using recent history
        levels_df = df.iloc[-80:-5]
        res_level = levels_df['high'].max()
        sup_level = levels_df['low'].min()
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        signals = []
        
        # 2. Confluences
        avg_body = (df['close'] - df['open']).abs().tail(20).mean()
        current_body = abs(current_candle['close'] - current_candle['open'])
        
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = current_candle['volume'] > (avg_vol * 1.5)
        
        # 3. Bullish Breakout
        if current_candle['close'] > res_level and prev_candle['close'] <= res_level:
            # Must be a relatively strong candle
            if current_body > avg_body:
                confidence = 0.7
                if vol_spike: confidence += 0.15
                
                signals.append(Signal(
                    signal_type=SignalType.BUY,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=res_level * 0.995,
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Bullish Breakout above {res_level:.2f}. "
                              f"{'High volume confirmation.' if vol_spike else ''}"
                ))
                
        # 4. Bearish Breakdown
        elif current_candle['close'] < sup_level and prev_candle['close'] >= sup_level:
            if current_body > avg_body:
                confidence = 0.7
                if vol_spike: confidence += 0.15
                
                signals.append(Signal(
                    signal_type=SignalType.SELL,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=sup_level * 1.005,
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Bearish Breakdown below {sup_level:.2f}. "
                              f"{'High volume confirmation.' if vol_spike else ''}"
                ))
                
        return signals
