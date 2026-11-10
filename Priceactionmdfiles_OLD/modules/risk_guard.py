"""
RiskGuard — hard kill switch for drawdown periods.
Engages on: daily loss, weekly loss, consecutive losing streak.
State persisted to disk so crashes don't reset the breaker.
"""
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import json
from typing import Tuple

logger = logging.getLogger("RiskGuard")

STATE_FILE = Path("data/risk_guard_state.json")

class RiskGuard:
    def __init__(self,
                 starting_capital: float = 50000.0,
                 daily_loss_pct: float = 3.0,      # configurable
                 weekly_loss_pct: float = 6.0,
                 streak_limit: int = 5,
                 cooldown_after_daily: timedelta = timedelta(hours=24),
                 cooldown_after_weekly: timedelta = timedelta(days=3),
                 cooldown_after_streak: timedelta = timedelta(hours=4)):
        self.capital = starting_capital
        self.daily_limit_amt   = starting_capital * daily_loss_pct  / 100
        self.weekly_limit_amt  = starting_capital * weekly_loss_pct / 100
        self.streak_limit      = streak_limit
        self.cd_daily   = cooldown_after_daily
        self.cd_weekly  = cooldown_after_weekly
        self.cd_streak  = cooldown_after_streak
        self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    s = json.load(f)
                self.day_pnl       = s.get('day_pnl', 0.0)
                self.day_anchor    = s.get('day_anchor')                 # YYYY-MM-DD str
                self.week_pnl      = s.get('week_pnl', 0.0)
                self.week_anchor   = s.get('week_anchor')                # ISO week str
                self.loss_streak   = s.get('loss_streak', 0)
                self.cooldown_until= s.get('cooldown_until')             # ISO datetime str or None
                self.trip_reason   = s.get('trip_reason')
            except Exception as e:
                logger.warning(f"Failed to load RiskGuard state: {e}. Resetting.")
                self._reset_internal_vars()
        else:
            self._reset_internal_vars()

    def _reset_internal_vars(self):
        self.day_pnl = 0.0
        self.day_anchor = None
        self.week_pnl = 0.0
        self.week_anchor = None
        self.loss_streak = 0
        self.cooldown_until = None
        self.trip_reason = None

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'day_pnl': self.day_pnl,
                'day_anchor': self.day_anchor,
                'week_pnl': self.week_pnl,
                'week_anchor': self.week_anchor,
                'loss_streak': self.loss_streak,
                'cooldown_until': self.cooldown_until,
                'trip_reason': self.trip_reason,
            }, f, indent=2)

    def _roll_periods(self, now: datetime):
        today = now.date().isoformat()
        if self.day_anchor != today:
            self.day_pnl = 0.0
            self.day_anchor = today
        
        # ISO Week: YYYY-Www
        wk = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
        if self.week_anchor != wk:
            self.week_pnl = 0.0
            self.week_anchor = wk

    def can_trade(self, now: datetime = None) -> Tuple[bool, str]:
        """Call before placing every order. Returns (allowed, reason)."""
        now = now or datetime.now()
        self._roll_periods(now)
        
        if self.cooldown_until:
            cd_dt = datetime.fromisoformat(self.cooldown_until)
            if now < cd_dt:
                return False, f"COOLDOWN_{self.trip_reason} until {self.cooldown_until}"
            
            # Cooldown expired
            logger.info(f"RiskGuard cooldown ({self.trip_reason}) expired. Resuming.")
            self.cooldown_until = None
            self.trip_reason = None
            self._save_state()
            
        return True, "OK"

    def record_trade(self, pnl: float, now: datetime = None):
        """Call AFTER each trade closes. Updates state and may trip breaker."""
        now = now or datetime.now()
        self._roll_periods(now)
        self.day_pnl  += pnl
        self.week_pnl += pnl
        if pnl < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

        # Trip checks (most severe first)
        if self.week_pnl <= -self.weekly_limit_amt:
            self.cooldown_until = (now + self.cd_weekly).isoformat()
            self.trip_reason = "WEEKLY_LOSS"
            logger.warning(f"RiskGuard TRIPPED: Weekly loss {self.week_pnl:.2f} <= -{self.weekly_limit_amt:.2f}")
        elif self.day_pnl <= -self.daily_limit_amt:
            self.cooldown_until = (now + self.cd_daily).isoformat()
            self.trip_reason = "DAILY_LOSS"
            logger.warning(f"RiskGuard TRIPPED: Daily loss {self.day_pnl:.2f} <= -{self.daily_limit_amt:.2f}")
        elif self.loss_streak >= self.streak_limit:
            self.cooldown_until = (now + self.cd_streak).isoformat()
            self.trip_reason = "LOSS_STREAK"
            logger.warning(f"RiskGuard TRIPPED: Loss streak reached {self.loss_streak}")

        self._save_state()

    def reset(self):
        """Manual override (use only after capital top-up or strategy adjustment)."""
        self._reset_internal_vars()
        self._save_state()
        logger.info("RiskGuard manual reset performed.")
