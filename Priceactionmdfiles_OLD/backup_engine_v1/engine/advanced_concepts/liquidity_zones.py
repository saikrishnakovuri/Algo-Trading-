"""
Strategy: Liquidity Zones
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Liquidity Zones.md

Description:
  Liquidity Zones are areas where large clusters of orders (stop losses, pending orders) reside.
  - Buy-Side Liquidity: Above swing highs, EQH.
  - Sell-Side Liquidity: Below swing lows, EQL.

Logic:
  - Institutions target these areas to fill large orders.
  - A "Sweep" or "Grab" occurs when price briefly breaks these levels and then reverses sharply.
  - Validated by volume spikes and quick rejection (wick).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class LiquidityZones(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Liquidity Zones"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
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
            
        swings = self._find_swings(df)
        high_indices = swings['highs']
        low_indices = swings['lows']
        
        if len(high_indices) < 1 or len(low_indices) < 1:
            return []
            
        signals = []
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Volume confirmation
        avg_vol = df['volume'].tail(20).mean()
        vol_spike = current_candle['volume'] > (avg_vol * 1.5)
        
        # 1. Check for Sell-Side Liquidity Sweep (Bullish Reversal)
        # Price goes below a recent swing low and closes back above it
        recent_low_indices = [l for l in low_indices if l < len(df) - 1 and l > len(df) - 50]
        if recent_low_indices:
            last_low_idx = recent_low_indices[-1]
            last_low = df['low'].iloc[last_low_idx]
            
            # Condition: Current low < last_low AND current close > last_low
            if current_candle['low'] < last_low and current_candle['close'] > last_low:
                confidence = 0.7
                if vol_spike: confidence += 0.15
                
                signals.append(Signal(
                    signal_type=SignalType.BUY,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=current_candle['low'],
                    market_bias=MarketBias.BULLISH,
                    reasoning=f"Sell-Side Liquidity Sweep: Price grabbed liquidity below {last_low:.2f} and rejected. "
                              f"{'Volume spike confirmed.' if vol_spike else ''}"
                ))

        # 2. Check for Buy-Side Liquidity Sweep (Bearish Reversal)
        # Price goes above a recent swing high and closes back below it
        recent_high_indices = [h for h in high_indices if h < len(df) - 1 and h > len(df) - 50]
        if recent_high_indices:
            last_high_idx = recent_high_indices[-1]
            last_high = df['high'].iloc[last_high_idx]
            
            # Condition: Current high > last_high AND current close < last_high
            if current_candle['high'] > last_high and current_candle['close'] < last_high:
                confidence = 0.7
                if vol_spike: confidence += 0.15
                
                signals.append(Signal(
                    signal_type=SignalType.SELL,
                    strategy_name=self.name,
                    confidence=min(confidence, 1.0),
                    timeframe=timeframe,
                    entry_price=current_candle['close'],
                    stop_loss=current_candle['high'],
                    market_bias=MarketBias.BEARISH,
                    reasoning=f"Buy-Side Liquidity Sweep: Price grabbed liquidity above {last_high:.2f} and rejected. "
                              f"{'Volume spike confirmed.' if vol_spike else ''}"
                ))

        # 3. Check for Equal Highs/Lows (Potential Target Zones)
        # If we are near but haven't swept yet
        if not signals:
            # Check for EQH
            if len(high_indices) >= 2:
                h1 = df['high'].iloc[high_indices[-1]]
                h2 = df['high'].iloc[high_indices[-2]]
                if abs(h1 - h2) / h1 < 0.001: # 0.1% tolerance
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.5,
                        timeframe=timeframe,
                        market_bias=MarketBias.NEUTRAL,
                        reasoning=f"Equal Highs detected near {h1:.2f}. Potential Buy-Side Liquidity pool."
                    ))
            # Check for EQL
            if len(low_indices) >= 2:
                l1 = df['low'].iloc[low_indices[-1]]
                l2 = df['low'].iloc[low_indices[-2]]
                if abs(l1 - l2) / l1 < 0.001:
                    signals.append(Signal(
                        signal_type=SignalType.HOLD,
                        strategy_name=self.name,
                        confidence=0.5,
                        timeframe=timeframe,
                        market_bias=MarketBias.NEUTRAL,
                        reasoning=f"Equal Lows detected near {l1:.2f}. Potential Sell-Side Liquidity pool."
                    ))

        return signals
