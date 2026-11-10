"""
UNIFIED STRATEGY ENGINE
Combines 48 new pattern-based strategies with the 'Old Engine' 
Regime Filtering and Contextual Logic.
"""

import pandas as pd
import numpy as np
from engine.strategy_engine import StrategyEngine
from engine.signal import Signal, SignalType
from modules.regime.integration import MarketRegimeAdapter

class UnifiedStrategyEngine:
    def __init__(self):
        # 1. New Pattern-based Engine (48 strategies)
        self.pattern_engine = StrategyEngine()
        
        # 2. Old Regime-based Adapter
        self.regime_adapter = MarketRegimeAdapter()
        
    def get_signals(self, df: pd.DataFrame, timeframe: str = "15m", symbol: str = "UNKNOWN", backtest_mode: bool = False) -> list:
        """
        Runs all 48 strategies and then filters/augments them 
        using the old engine's regime and context logic.
        """
        # Reset index to handle strategies that use integer indexing with .loc or idxmax
        df_reset = df.reset_index()
        
        # A. Detect patterns using new engine
        raw_signals = self.pattern_engine.detect_all(df_reset)
        
        # B. Get market regime using old engine logic
        # mtf_analyses expected by regime_adapter
        mtf_analyses = {timeframe: df} 
        regime_decision = self.regime_adapter.get_regime_decision(mtf_analyses, backtest_mode=backtest_mode)
        
        # C. Filter and Augment
        filtered_signals = []
        curr_time = df.index[-1].time()
        
        for sig in raw_signals:
            # Skip HOLD signals
            if sig.signal_type == SignalType.HOLD:
                continue
                
            # Apply Regime Filter (Old Engine Logic)
            if not self.is_signal_allowed_in_regime(sig, regime_decision.regime):
                continue
            
            # --- PRODUCTION VETO GATES ---
            direction = 'BULLISH' if sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
            
            # 1. Time Gate
            from datetime import time as dtime
            if curr_time < dtime(9, 45) or curr_time > dtime(14, 45):
                continue # Blocking opening burst and late EOD entries
                
            # 2. Afternoon CE Veto
            if direction == 'BULLISH' and curr_time >= dtime(13, 30):
                if sig.confidence < 0.75:
                    continue # Veto low-confidence afternoon longs
                    
            # 3. Momentum Confirmation (Last 3 closes)
            if len(df) >= 3:
                last_3 = df['close'].iloc[-3:].values
                if direction == 'BULLISH' and not (last_3[2] > last_3[0]):
                    continue
                if direction == 'BEARISH' and not (last_3[2] < last_3[0]):
                    continue
            
            # Augment with regime info
            sig.metadata['regime'] = regime_decision.regime
            filtered_signals.append(sig)
            
        return filtered_signals

    def is_signal_allowed_in_regime(self, signal: Signal, regime: str) -> bool:
        """
        Old engine logic: Certain regimes block certain setup types.
        """
        if regime == "VOLATILE" and signal.confidence < 0.70:
            return False # Only high confidence in volatile markets
        if regime == "CHOPPY" or regime == "CHOPPY_UNTRADEABLE":
            return False # No trades in choppy markets
        if regime == "TRENDING_UP" and signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            return signal.confidence > 0.80 # Only very strong reversals
        if regime == "TRENDING_DOWN" and signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            return signal.confidence > 0.80
        return True

    def get_summary(self, df: pd.DataFrame, timeframe: str = "15m", symbol: str = "UNKNOWN") -> dict:
        signals = self.get_signals(df, timeframe, symbol)
        
        bullish = [s for s in signals if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]]
        bearish = [s for s in signals if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]]
        
        # Overall bias
        bias = "NEUTRAL"
        if len(bullish) > len(bearish) * 1.5: bias = "BULLISH"
        elif len(bearish) > len(bullish) * 1.5: bias = "BEARISH"
        
        return {
            'bias': bias,
            'bullish_count': len(bullish),
            'bearish_count': len(bearish),
            'signals': signals,
            'top_signals': sorted([s.to_dict() for s in signals], key=lambda x: x['confidence'], reverse=True)[:5]
        }
