import logging
from datetime import datetime, timedelta, time
import threading

logger = logging.getLogger("OptionsRisk")

class OptionsRiskManager:
    """
    Implements strict anti-ruin and portfolio-level risk rules for 
    Index Option buying.
    """
    
    def __init__(self, total_capital=500000.0):
        self.total_capital = total_capital
        self.risk_per_trade_pct = 0.01
        self.daily_circuit_breaker_pct = 0.02
        self._lock = threading.Lock()
        
        # Daily/Weekly Counters
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0
        self.last_loss_time = None
        
        # Risk Limits (Based on current portfolio equity)
        self.max_daily_loss = -(self.total_capital * self.daily_circuit_breaker_pct)
        self.max_weekly_loss = -50000.0 # -10% Weekly Breaker 
        self.daily_trade_limit = 3 # 3 Trades max per day
        self.profit_lock_threshold = 25000.0 # Lock after +5% gain
        
        # Current State
        self.is_weekly_blocked = False
        self.is_daily_blocked = False

    def can_trade(self, symbol: str, current_ts: datetime) -> tuple:
        """
        Final check before allowing a signal to proceed to the strike selector.
        Returns: (bool, reason)
        """
        with self._lock:
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

    def update_total_equity(self, total_equity: float):
        """Keep risk limits tied to the current compounded portfolio equity."""
        with self._lock:
            self.total_capital = float(total_equity)
            self.max_daily_loss = -(self.total_capital * self.daily_circuit_breaker_pct)

    def get_position_size(self, symbol: str, premium: float, sl_points: float) -> int:
        """
        Calculates quantity using the validated 1% max-risk rule.

        Hard limits:
        - NIFTY options: 5 lots max = 325 qty.
        - BANKNIFTY options: 5 lots max = 150 qty.
        - Equity paper trades: 75 shares max.
        """
        effective_sl = float(sl_points or 0.0)
        if effective_sl <= 0:
            return 0

        risk_per_trade = self.total_capital * self.risk_per_trade_pct
        raw_qty = int(risk_per_trade // effective_sl)

        symbol_upper = (symbol or "").upper()
        if symbol_upper == "NIFTY":
            lot_size = 65
            # Force exactly 1 lot if raw_qty allows it, otherwise 0
            lots = 1 if raw_qty >= lot_size else 0
            qty = lots * lot_size
        elif symbol_upper in {"BANKNIFTY", "BANKNIFTY_OPTIONS"}:
            lot_size = 30
            # Force exactly 1 lot if raw_qty allows it, otherwise 0
            lots = 1 if raw_qty >= lot_size else 0
            qty = lots * lot_size
        else:
            qty = min(75, max(0, raw_qty))
        
        with self._lock:
            # Profit Lock Check
            if self.daily_pnl >= self.profit_lock_threshold:
                qty = max(1, int(qty * 0.5))
                logger.info(f"PROFIT LOCK: Daily PnL > {self.profit_lock_threshold}. Reducing size.")

        return qty

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
        with self._lock:
            if self.consecutive_losses == 0:
                return base_threshold
            
            escalation = self.consecutive_losses * 5
            final_hurdle = min(90, base_threshold + escalation)
            
            if escalation > 0:
                logger.info(f"CONFIDENCE LADDER: Loss streak {self.consecutive_losses}. Hurdle raised to {final_hurdle}%")
                
            return final_hurdle

    def record_trade(self, net_pnl: float, ts: datetime):
        """Updates internal risk trackers after a trade closes."""
        with self._lock:
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
        with self._lock:
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.is_daily_blocked = False
            self.consecutive_losses = max(0, self.consecutive_losses - 1)
            logger.info(f"DAILY RESET: Counters cleared. Loss Memory: {self.consecutive_losses}")

    def weekly_reset(self):
        """Call on Monday open."""
        with self._lock:
            self.weekly_pnl = 0.0
            self.is_weekly_blocked = False
            logger.info("WEEKLY RESET: Portfolio state refreshed.")

    def get_risk_status(self) -> dict:
        with self._lock:
            return {
                'daily_pnl': round(self.daily_pnl, 2),
                'trades': self.trades_today,
                'consecutive_losses': self.consecutive_losses,
                'daily_blocked': self.is_daily_blocked,
                'weekly_blocked': self.is_weekly_blocked
            }
