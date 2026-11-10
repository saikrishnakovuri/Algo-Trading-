from datetime import datetime
from typing import Dict, Any, Optional
from modules.risk_exec.schemas import RiskStatus

class DrawdownCircuitBreaker:
    """
    Tiered drawdown circuit breaker and consecutive loss tracker.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['drawdown']
        self.consecutive_losses = 0
        self.session_pnl_accum = 0.0
        
    def get_status(self, day_start_equity: float) -> RiskStatus:
        if day_start_equity <= 0:
            return self._halt("INVALID_EQUITY")
            
        pnl_pct = self.session_pnl_accum / day_start_equity * 100
        
        # Tiers
        tier = 0
        if pnl_pct < self.config['tiers']['halt_threshold_pct']: tier = 4
        elif pnl_pct < self.config['tiers']['tier3_threshold_pct']: tier = 3
        elif pnl_pct < self.config['tiers']['tier2_threshold_pct']: tier = 2
        elif pnl_pct < self.config['tiers']['tier1_threshold_pct']: tier = 1
        
        # Override if consecutive losses
        mult = self.config['size_multipliers'][tier]
        if self.consecutive_losses >= self.config['consecutive_losses']['reduce_after']:
            mult *= self.config['consecutive_losses']['reduce_multiplier']
            
        if self.consecutive_losses >= self.config['consecutive_losses']['halt_after']:
            tier = 4
            mult = 0.0

        reasoning = f"Session PnL: {pnl_pct:.2f}%. Consecutive Losses: {self.consecutive_losses}."
        
        return RiskStatus(
            tier=tier,
            size_multiplier=mult,
            min_tier_allowed=self.config['min_tier_allowed'][tier],
            max_open_trades=self.config['max_open_trades'][tier],
            session_pnl_pct=round(pnl_pct, 2),
            consecutive_losses=self.consecutive_losses,
            halt_until=None if tier < 4 else datetime.now(), # Simple logic
            reasoning=reasoning
        )

    def record_trade(self, pnl: float):
        self.session_pnl_accum += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_session(self):
        self.session_pnl_accum = 0.0
        # self.consecutive_losses = 0 # Instructions say "across sessions" for some counters

    def _halt(self, reason: str) -> RiskStatus:
        return RiskStatus(4, 0.0, None, 0, 0.0, 0, datetime.now(), reason)
