import logging
from datetime import datetime, timedelta, time

logger = logging.getLogger("OptionsRisk")

class OptionsRiskManager:
    """
    Implements strict anti-ruin and portfolio-level risk rules for 
    Index Option buying.
    """
    
    def __init__(self, total_capital=100000.0):
        self.total_capital = total_capital
        
        # Daily/Weekly Counters
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0
        self.last_loss_time = None
        
        # Risk Limits (Based on 1L Capital)
        self.max_daily_loss = -2000.0 # -2% Daily Circuit Breaker
        self.max_weekly_loss = -10000.0 # -10% Weekly Breaker 
        self.daily_trade_limit = 3 # 3 Trades max per day
        self.profit_lock_threshold = 5000.0 # Lock after +5% gain
        
        # Current State
        self.is_weekly_blocked = False
        self.is_daily_blocked = False

    def can_trade(self, symbol: str, current_ts: datetime) -> tuple:
        """
        Final check before allowing a signal to proceed to the strike selector.
        Returns: (bool, reason)
        """
        # 1. Block Check
        if self.is_weekly_blocked:
            return False, "WEEKLY_CIRCUIT_BREAKER_HIT"
        if self.is_daily_blocked or self.daily_pnl <= self.max_daily_loss:
            self.is_daily_blocked = True
            return False, "DAILY_LOSS_LIMIT_HIT"
            
        # 2. Trade Count Check
        if self.trades_today >= self.daily_trade_limit:
            return False, "DAILY_TRADE_LIMIT_REACHED"
            
        # 3. 1-Loss Rule: Stop for the day after ANY loss
        if self.consecutive_losses >= 1:
            return False, "DAILY_LOSS_LIMIT_HIT (1-LOSS-RULE)"
                    
        return True, "ALLOWED"

    def get_position_size(self, symbol: str, premium: float, sl_points: float) -> int:
        """
        Calculates optimal quantity based on 2% risk rule.
        Qty = Risk / SL_Points
        """
        risk_per_trade = self.total_capital * 0.02
        
        if sl_points <= 0: return 0
        
        raw_qty = risk_per_trade / sl_points
        
        # Adjust for Lot Sizes (User Specified: Nifty 65, BN 30)
        lot_size = 65 if symbol == "NIFTY" else 30
        lots = max(1, round(raw_qty / lot_size))
        
        # Cap for safety
        max_lots = 5 if symbol == "BANKNIFTY" else 2
        lots = min(max_lots, lots)
        
        # Profit Lock Check
        if self.daily_pnl >= self.profit_lock_threshold:
            lots = max(1, int(lots * 0.5))
            logger.info(f"PROFIT LOCK: Daily PnL > {self.profit_lock_threshold}. Reducing size.")

        return lots * lot_size

    def check_correlation(self, signals: list) -> bool:
        """
        Checks if NIFTY and BANKNIFTY signals are conflicting.
        Returns True if they agree or only one signal exists.
        """
        if len(signals) < 2:
            return True
            
        directions = [s['options_direction'] for s in signals]
        if "CE" in directions and "PE" in directions:
            logger.warning("CORRELATION: Conflict detected between Nifty/BNF. Skipping both.")
            return False
            
        return True

    def get_required_confidence(self, base_threshold: int) -> int:
        """
        Confidence Escalation Ladder
        Increases hurdle rate after losses.
        """
        if self.consecutive_losses == 0:
            return base_threshold
        
        escalation = self.consecutive_losses * 5
        final_hurdle = min(90, base_threshold + escalation)
        
        if escalation > 0:
            logger.info(f"CONFIDENCE LADDER: Loss streak {self.consecutive_losses}. Hurdle raised to {final_hurdle}%")
            
        return final_hurdle

    def record_trade(self, net_pnl: float, ts: datetime):
        """Updates internal risk trackers after a trade closes."""
        self.daily_pnl += net_pnl
        self.weekly_pnl += net_pnl
        self.trades_today += 1
        
        if net_pnl < 0:
            self.consecutive_losses += 1
            self.last_loss_time = ts
        else:
            self.consecutive_losses = 0 # Reset streak on any win
            
        # Daily Circuit Breaker
        if self.daily_pnl <= self.max_daily_loss:
            self.is_daily_blocked = True
            logger.error(f"CIRCUIT BREAKER: Daily Loss Limit of {self.max_daily_loss} Hit.")

        # Weekly Circuit Breaker
        if self.weekly_pnl <= self.max_weekly_loss:
            self.is_weekly_blocked = True
            logger.error(f"WEEKLY BREAKER: Weekly Loss Limit of {self.max_weekly_loss} Hit.")

    def daily_reset(self):
        """Reset daily counters at morning open."""
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.is_daily_blocked = False
        self.consecutive_losses = max(0, self.consecutive_losses - 1)
        logger.info(f"DAILY RESET: Counters cleared. Loss Memory: {self.consecutive_losses}")

    def weekly_reset(self):
        """Call on Monday open."""
        self.weekly_pnl = 0.0
        self.is_weekly_blocked = False
        logger.info("WEEKLY RESET: Portfolio state refreshed.")

    def get_risk_status(self) -> dict:
        return {
            'daily_pnl': round(self.daily_pnl, 2),
            'trades': self.trades_today,
            'consecutive_losses': self.consecutive_losses,
            'daily_blocked': self.is_daily_blocked,
            'weekly_blocked': self.is_weekly_blocked
        }
