import pandas as pd
from typing import Dict, Any, Optional
from modules.risk_exec.schemas import ApprovedSignal

class ExecutionQualityTracker:
    """
    Models slippage, market impact, and commissions for realistic backtesting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['execution']
        
    def model_execution(self, signal: ApprovedSignal, qty: int, tick_size: float = 0.05) -> Dict[str, float]:
        
        # 1. Base Slippage
        # Mapping liquidity tier to ticks
        liquidity = signal.metadata.get('liquidity_tier', 'medium_liquidity')
        ticks = self.config['slippage_ticks_by_tier'].get(liquidity, 2)
        
        base_slippage = ticks * tick_size
        
        # 2. Market Impact
        # order_value > 0.1% of ADV
        impact_slippage_bps = 0.0
        adv = signal.metadata.get('stock_adv', 1e9)
        order_value = qty * signal.entry_price
        
        if order_value > self.config['market_impact_threshold_adv'] * adv:
            impact_slippage_bps = (order_value / adv) * self.config['market_impact_bps_per_adv_unit']
            impact_slippage_bps = min(impact_slippage_bps, self.config['market_impact_cap_bps'])
            
        impact_slippage = (impact_slippage_bps / 10000.0) * signal.entry_price
        
        total_slippage = base_slippage + impact_slippage
        
        # Adverse direction
        if signal.direction == "LONG":
            actual_entry = signal.entry_price + total_slippage
        else:
            actual_entry = signal.entry_price - total_slippage
            
        # 3. Commissions (0.1% round-trip)
        cost_pct = self.config['round_trip_cost_pct'] / 100.0
        # In backtest we can deduct entire round-trip at entry or split it.
        # deducting at entry for simplicity
        commissions = order_value * cost_pct
        
        return {
            'expected_entry': signal.entry_price,
            'actual_entry': round(actual_entry, 2),
            'slippage_per_share': round(total_slippage, 4),
            'commission_cost': round(commissions, 2)
        }
