import numpy as np
import pandas as pd
try:
    from typing import List, Dict, Any, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import List, Dict, Any, Optional, Union
    Literal = Any
from modules.smc.schemas import StructureState, OrderBlock

class StructureTracker:
    """
    Tracks market structure (BOS, CHoCH, MSS) and manages Breaker Blocks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['smc']['structure']
        self.state = StructureState(current_state="TRANSITIONING")
        self.swings: List[Dict[str, Any]] = [] # list of {price, type, bar_idx}
        
    def update(self, df: pd.DataFrame, atr: float, invalidated_obs: List[OrderBlock]) -> StructureState:
        """
        Incremental update: detects swings and structure events.
        """
        if len(df) < 20: return self.state
        
        # 1. Update Swings (Zigzag)
        self._detect_swings(df, atr)
        
        # 2. Check for BOS / CHoCH / MSS
        self._analyze_structure(df)
        
        # 3. Track Breaker Blocks
        for ob in invalidated_obs:
            if ob not in self.state.breaker_blocks:
                self.state.breaker_blocks.append(ob)
                
        # Cleanup old breakers
        # ...
        
        return self.state

    def _detect_swings(self, df: pd.DataFrame, atr: float):
        # Simplified Zigzag: using fixed threshold
        threshold = self.config.get('zigzag_threshold_atr', 0.5) * atr
        
        if not self.swings:
            # Init first swing
            self.swings.append({'price': df['high'].iloc[0], 'type': 'HIGH', 'bar_idx': 0})
            
        for i in range(len(df)):
            last = self.swings[-1]
            price_h = df['high'].iloc[i]
            price_l = df['low'].iloc[i]
            
            if last['type'] == 'HIGH':
                if price_h > last['price']:
                    # Update current high
                    last['price'] = price_h
                    last['bar_idx'] = i
                elif price_l < last['price'] - threshold:
                    # Found new low
                    self.swings.append({'price': price_l, 'type': 'LOW', 'bar_idx': i})
            else: # last was LOW
                if price_l < last['price']:
                    last['price'] = price_l
                    last['bar_idx'] = i
                elif price_h > last['price'] + threshold:
                    self.swings.append({'price': price_h, 'type': 'HIGH', 'bar_idx': i})

        # Update last swings in state
        highs = [s for s in self.swings if s['type'] == 'HIGH']
        lows = [s for s in self.swings if s['type'] == 'LOW']
        
        if len(highs) >= 2:
            h1, h2 = highs[-2], highs[-1]
            if h2['price'] > h1['price']: 
                self.state.last_swing_HH = h2['price']
                self.state.last_swing_LH = None
            else: 
                self.state.last_swing_LH = h2['price']
                self.state.last_swing_HH = None
            
        if len(lows) >= 2:
            l1, l2 = lows[-2], lows[-1]
            if l2['price'] > l1['price']: 
                self.state.last_swing_HL = l2['price']
                self.state.last_swing_LL = None
            else: 
                self.state.last_swing_LL = l2['price']
                self.state.last_swing_HL = None

    def _analyze_structure(self, df: pd.DataFrame):
        if len(self.swings) < 4: return
        
        latest_close = df['close'].iloc[-1]
        i = len(df) - 1
        
        highs = [s for s in self.swings if s['type'] == 'HIGH']
        lows = [s for s in self.swings if s['type'] == 'LOW']
        
        # 1. CHoCH Detection: Violation of established trend
        # Uptrend: HH, HL. CHoCH = close below last HL.
        if len(highs) >= 2 and len(lows) >= 2:
            # Established Uptrend?
            if highs[-2]['price'] < highs[-1]['price'] and lows[-2]['price'] < lows[-1]['price']:
                if latest_close < lows[-1]['price']:
                    if not self.state.last_CHoCH or self.state.last_CHoCH['direction'] == 'BULL':
                        self.state.last_CHoCH = {'direction': 'BEAR', 'price': latest_close, 'bar_idx': i}
            
            # Established Downtrend?
            elif highs[-2]['price'] > highs[-1]['price'] and lows[-2]['price'] > lows[-1]['price']:
                if latest_close > highs[-1]['price']:
                    if not self.state.last_CHoCH or self.state.last_CHoCH['direction'] == 'BEAR':
                        self.state.last_CHoCH = {'direction': 'BULL', 'price': latest_close, 'bar_idx': i}
        
        # 2. Case where the new LOW itself is the violation
        if len(lows) >= 3 and self.state.current_state == "UPTREND":
             if lows[-1]['price'] < lows[-2]['price']:
                  self.state.last_CHoCH = {'direction': 'BEAR', 'price': latest_close, 'bar_idx': i}

        if len(highs) >= 3 and self.state.current_state == "DOWNTREND":
             if highs[-1]['price'] > highs[-2]['price']:
                  self.state.last_CHoCH = {'direction': 'BULL', 'price': latest_close, 'bar_idx': i}

        # Update live trend state for BOS
        if self.state.last_swing_HH and self.state.last_swing_HL:
            curr_trend = "UPTREND"
        elif self.state.last_swing_LH and self.state.last_swing_LL:
            curr_trend = "DOWNTREND"
        else:
            curr_trend = "TRANSITIONING"
            
        # BOS: Continuation
        if curr_trend == "UPTREND" and self.state.last_swing_HH:
            if latest_close > self.state.last_swing_HH:
                self.state.last_BOS = {'direction': 'BULL', 'price': latest_close, 'bar_idx': i}
        elif curr_trend == "DOWNTREND" and self.state.last_swing_LL:
            if latest_close < self.state.last_swing_LL:
                self.state.last_BOS = {'direction': 'BEAR', 'price': latest_close, 'bar_idx': i}
                
        self.state.current_state = curr_trend
