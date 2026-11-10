import numpy as np
from typing import Dict, Any, Optional
from modules.smc.schemas import StructureState

class PremiumDiscountCalculator:
    """
    Classifies price based on its position within the last confirmed impulse leg (OTE zones).
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['smc']['premium_discount']
        
    def calculate(self, current_price: float, structure: StructureState) -> Dict[str, Any]:
        """
        Determines if price is in Premium, Discount, or OTE zones.
        """
        # Impulse leg depends on current structure
        # Bullish leg: last swing low -> last swing high
        # Bearish leg: last swing high -> last swing low
        
        low = structure.last_swing_HL or structure.last_swing_LL
        high = structure.last_swing_HH or structure.last_swing_LH
        
        if low is None or high is None or low == high:
            return {'zone': 'EQUILIBRIUM', 'ote_dist': 0.0}
            
        # Determine Fibonacci levels
        total_range = high - low
        
        if structure.current_state == "UPTREND":
            # For longs, we want DISCOUNT (< 0.5)
            # Retracement % from the high
            retrace = (high - current_price) / total_range
            
            # Ratios from brief:
            # 0.5 = equilibrium
            # 0.618 = OTE start
            # 0.79 = OTE end
            
            if retrace < 0.5: zone = "PREMIUM" # High prices in uptrend
            elif 0.5 <= retrace < 0.618: zone = "EQUILIBRIUM"
            elif 0.618 <= retrace <= 0.79: zone = "OTE"
            else: zone = "DISCOUNT" # Very deep retrace
            
        elif structure.current_state == "DOWNTREND":
            # For shorts, we want PREMIUM (High prices relative to the drop)
            retrace = (current_price - low) / total_range
            
            if retrace < 0.5: zone = "DISCOUNT" # Low prices in downtrend
            elif 0.5 <= retrace < 0.618: zone = "EQUILIBRIUM"
            elif 0.618 <= retrace <= 0.79: zone = "OTE"
            else: zone = "PREMIUM"
        else:
            zone = "EQUILIBRIUM"
            retrace = 0.5
            
        return {
            'zone': zone,
            'retrace_ratio': round(retrace, 3),
            'leg_low': low,
            'leg_high': high
        }
