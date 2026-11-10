"""
UNIFIED STRATEGY ENGINE
 Central hub that runs all 48 Price Action Strategies.
"""

import pandas as pd
import os
import inspect
from typing import List, Dict, Type
from .base_strategy import BaseStrategy
from .signal import Signal

# Import all strategies manually to avoid dynamic loading issues in complex environments
# and to ensure full control over instantiation.

# Section 1: Advanced Concepts
from .advanced_concepts.market_structure import MarketStructure
from .advanced_concepts.higher_high_higher_low import HigherHighHigherLow
from .advanced_concepts.lower_high_lower_low import LowerHighLowerLow
from .advanced_concepts.break_of_structure_bos import BreakOfStructure
from .advanced_concepts.change_of_character_choch import ChangeOfCharacter
from .advanced_concepts.order_blocks import OrderBlocks
from .advanced_concepts.fair_value_gaps_fvg import FairValueGaps
from .advanced_concepts.supply_demand import SupplyDemand
from .advanced_concepts.liquidity_zones import LiquidityZones

# Section 2: Candlestick Patterns
from .candlestick_patterns.bearish_engulfing import BearishEngulfing
from .candlestick_patterns.bullish_engulfing import BullishEngulfing
from .candlestick_patterns.dark_cloud_cover import DarkCloudCover
from .candlestick_patterns.doji import Doji
from .candlestick_patterns.evening_star import EveningStar
from .candlestick_patterns.hammer import Hammer
from .candlestick_patterns.morning_star import MorningStar
from .candlestick_patterns.neutral_patterns import NeutralPatterns
from .candlestick_patterns.piercing_pattern import PiercingPattern
from .candlestick_patterns.shooting_star import ShootingStar
from .candlestick_patterns.spinning_top import SpinningTop

# Section 3: Price Action Patterns
from .price_action_patterns.ascending_channel import AscendingChannel
from .price_action_patterns.ascending_triangle import AscendingTriangle
from .price_action_patterns.bear_flag import BearFlag
from .price_action_patterns.bull_flag import BullFlag
from .price_action_patterns.cup_and_handle import CupAndHandle
from .price_action_patterns.descending_channel import DescendingChannel
from .price_action_patterns.descending_triangle import DescendingTriangle
from .price_action_patterns.double_bottom import DoubleBottom
from .price_action_patterns.double_top import DoubleTop
from .price_action_patterns.falling_wedge import FallingWedge
from .price_action_patterns.head_and_shoulders import HeadAndShoulders
from .price_action_patterns.horizontal_channel import HorizontalChannel
from .price_action_patterns.inverse_head_and_shoulders import InverseHeadAndShoulders
from .price_action_patterns.rectangle_range import RectangleRange
from .price_action_patterns.rising_wedge import RisingWedge
from .price_action_patterns.standard_head_and_shoulders import StandardHeadAndShoulders
from .price_action_patterns.symmetrical_triangle import SymmetricalTriangle
from .price_action_patterns.triple_bottom import TripleBottom
from .price_action_patterns.triple_top import TripleTop

# Section 4: Support & Resistance
from .support_resistance.breakout_retest_continuation import BreakoutRetestContinuation
from .support_resistance.breakout_trap import BreakoutTrap
from .support_resistance.breakout import Breakout
from .support_resistance.liquidity_grab import LiquidityGrab
from .support_resistance.resistance_breakout import ResistanceBreakout
from .support_resistance.resistance import Resistance
from .support_resistance.retest_entry import RetestEntry
from .support_resistance.support_breakdown import SupportBreakdown
from .support_resistance.support import Support


class StrategyEngine:
    def __init__(self):
        # Instantiate all strategies
        self.strategies: List[BaseStrategy] = [
            # Advanced Concepts
            MarketStructure(), HigherHighHigherLow(), LowerHighLowerLow(),
            BreakOfStructure(), ChangeOfCharacter(), OrderBlocks(),
            FairValueGaps(), SupplyDemand(), LiquidityZones(),
            
            # Candlesticks
            BearishEngulfing(), BullishEngulfing(), DarkCloudCover(),
            Doji(), EveningStar(), Hammer(), MorningStar(),
            NeutralPatterns(), PiercingPattern(), ShootingStar(), SpinningTop(),
            
            # Price Action Patterns
            AscendingChannel(), AscendingTriangle(), BearFlag(), BullFlag(),
            CupAndHandle(), DescendingChannel(), DescendingTriangle(),
            DoubleBottom(), DoubleTop(), FallingWedge(), HeadAndShoulders(),
            HorizontalChannel(), InverseHeadAndShoulders(), RectangleRange(),
            RisingWedge(), StandardHeadAndShoulders(), SymmetricalTriangle(),
            TripleBottom(), TripleTop(),
            
            # Support & Resistance
            BreakoutRetestContinuation(), BreakoutTrap(), Breakout(),
            LiquidityGrab(), ResistanceBreakout(), Resistance(),
            RetestEntry(), SupportBreakdown(), Support()
        ]
        
    def detect_all(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        """
        Run all strategies on the provided DataFrame.
        """
        all_signals = []
        for strategy in self.strategies:
            try:
                signals = strategy.detect(df, timeframe)
                if signals:
                    all_signals.extend(signals)
            except Exception as e:
                print(f"Error running strategy {strategy.name}: {e}")
                
        # Deduplicate or sort by confidence
        all_signals.sort(key=lambda x: x.confidence, reverse=True)
        return all_signals

    def get_summary(self, df: pd.DataFrame, timeframe: str = "15m") -> dict:
        """
        Get a summary of market bias based on all strategies.
        """
        signals = self.detect_all(df, timeframe)
        
        bullish_signals = [s for s in signals if s.market_bias.value == "BULLISH" and s.signal_type.value in ["BUY", "STRONG_BUY"]]
        bearish_signals = [s for s in signals if s.market_bias.value == "BEARISH" and s.signal_type.value in ["SELL", "STRONG_SELL"]]
        
        total_confidence_bull = sum(s.confidence for s in bullish_signals)
        total_confidence_bear = sum(s.confidence for s in bearish_signals)
        
        overall_bias = "NEUTRAL"
        if total_confidence_bull > total_confidence_bear * 1.5:
            overall_bias = "BULLISH"
        elif total_confidence_bear > total_confidence_bull * 1.5:
            overall_bias = "BEARISH"
            
        return {
            "bias": overall_bias,
            "bullish_count": len(bullish_signals),
            "bearish_count": len(bearish_signals),
            "top_signals": [s.to_dict() for s in signals[:5]]
        }
