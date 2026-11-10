"""
Strategy: Market Structure
Category: advanced_concept
Source: ADVANCED PRICE ACTION CONCEPTS/Market Structure.md

Description:
  Market Structure is the sequence of highs and lows formed by price.
  It reveals who controls the market (Bullish, Bearish, or Consolidation).

Components:
  - Higher Highs (HH)
  - Higher Lows (HL)
  - Lower Highs (LH)
  - Lower Lows (LL)

Trend Logic:
  - Bullish: HH -> HL -> HH
  - Bearish: LL -> LH -> LL

Events:
  - BOS (Break of Structure): Trend continuation (breaking HH in uptrend or LL in downtrend).
  - MSS (Market Structure Shift): Trend reversal (breaking LH in downtrend or HL in uptrend).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class MarketStructure(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Market Structure"
    
    @property
    def category(self) -> str:
        return "advanced_concept"
    
    @property
    def required_candles(self) -> int:
        return 100  # Need enough history to identify swing points
    
    def _find_swings(self, df: pd.DataFrame, window: int = 2) -> Dict[str, List[int]]:
        """
        Identify swing highs and lows.
        A swing high is the highest high in a window of 2*window + 1 candles.
        """
        highs = df['high'].values
        lows = df['low'].values
        
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            # Swing High
            if all(highs[i] > highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                swing_highs.append(i)
            
            # Swing Low
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
        
        if len(high_indices) < 2 or len(low_indices) < 2:
            return []
            
        signals = []
        
        # Get latest two swing points
        last_h_idx = high_indices[-1]
        prev_h_idx = high_indices[-2]
        last_l_idx = low_indices[-1]
        prev_l_idx = low_indices[-2]
        
        last_h = df['high'].iloc[last_h_idx]
        prev_h = df['high'].iloc[prev_h_idx]
        last_l = df['low'].iloc[last_l_idx]
        prev_l = df['low'].iloc[prev_l_idx]
        
        current_price = df['close'].iloc[-1]
        
        # Determine current bias
        bias = MarketBias.NEUTRAL
        confidence = 0.5
        reasoning = ""
        
        # Bullish Structure: HH + HL
        is_hh = last_h > prev_h
        is_hl = last_l > prev_l
        
        # Bearish Structure: LL + LH
        is_ll = last_l < prev_l
        is_lh = last_h < prev_h
        
        if is_hh and is_hl:
            bias = MarketBias.BULLISH
            reasoning = "Higher High and Higher Low detected (Bullish Structure)."
            confidence = 0.7
        elif is_ll and is_lh:
            bias = MarketBias.BEARISH
            reasoning = "Lower Low and Lower High detected (Bearish Structure)."
            confidence = 0.7
            
        # Check for BOS (Break of Structure) - Trend Continuation
        if bias == MarketBias.BULLISH and current_price > last_h:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_l,
                market_bias=bias,
                reasoning=f"{reasoning} Bullish BOS occurred (Price broke HH)."
            ))
        elif bias == MarketBias.BEARISH and current_price < last_l:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strategy_name=self.name,
                confidence=0.8,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_h,
                market_bias=bias,
                reasoning=f"{reasoning} Bearish BOS occurred (Price broke LL)."
            ))
            
        # Check for MSS (Market Structure Shift) - Reversal
        # Bullish MSS: Break LH in downtrend
        if is_ll and is_lh and current_price > last_h:
            signals.append(Signal(
                signal_type=SignalType.STRONG_BUY,
                strategy_name=self.name,
                confidence=0.85,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_l,
                market_bias=MarketBias.BULLISH,
                reasoning="Bullish Market Structure Shift: Price broke Lower High in a Bearish Trend."
            ))
        # Bearish MSS: Break HL in uptrend
        elif is_hh and is_hl and current_price < last_l:
            signals.append(Signal(
                signal_type=SignalType.STRONG_SELL,
                strategy_name=self.name,
                confidence=0.85,
                timeframe=timeframe,
                entry_price=current_price,
                stop_loss=last_h,
                market_bias=MarketBias.BEARISH,
                reasoning="Bearish Market Structure Shift: Price broke Higher Low in a Bullish Trend."
            ))
            
        # If no BOS/MSS, but clear trend, provide HOLD with bias
        if not signals and bias != MarketBias.NEUTRAL:
            signals.append(Signal(
                signal_type=SignalType.HOLD,
                strategy_name=self.name,
                confidence=confidence,
                timeframe=timeframe,
                market_bias=bias,
                reasoning=reasoning
            ))
            
        return signals
