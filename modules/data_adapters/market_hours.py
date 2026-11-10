"""
modules/data_adapters/market_hours.py
"""
from datetime import datetime, time, date, timedelta
from typing import Optional
import pytz

from .base_adapter import MarketHoursConfig


# Hardcoded NSE holidays for safety (manually updated annually)
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 17),   # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 1),   # Diwali Balipratipada
    date(2026, 12, 25),  # Christmas
    # Add more from NSE official calendar each year
}


class MarketHoursChecker:
    """Universal market-hours utility — works across NSE / crypto / forex."""

    @staticmethod
    def is_open(adapter_name: str, now: Optional[datetime] = None) -> tuple[bool, str]:
        """
        Returns (is_open, reason).
        reason is a short human-readable string for logs.
        """
        if now is None:
            now = datetime.now(pytz.timezone("Asia/Kolkata"))

        if adapter_name == "binance":
            return True, "crypto 24/7"

        if adapter_name == "alphavantage":
            # Forex: Sunday 17:00 ET to Friday 17:00 ET
            # In IST: Monday 03:30 to Saturday 03:30
            ny_tz = pytz.timezone("America/New_York")
            ny_now = now.astimezone(ny_tz)
            weekday = ny_now.weekday()  # Mon=0, Sun=6
            hour = ny_now.hour

            # Closed: Saturday all day
            if weekday == 5:
                return False, "forex closed (Saturday NY time)"
            # Closed: Sunday before 17:00 ET
            if weekday == 6 and hour < 17:
                return False, "forex closed (Sunday before 17:00 ET)"
            # Closed: Friday after 17:00 ET
            if weekday == 4 and hour >= 17:
                return False, "forex closed (Friday after 17:00 ET)"
            return True, "forex open (24/5)"

        if adapter_name == "angelone":
            today = now.date()
            weekday = now.weekday()

            if weekday >= 5:
                return False, f"NSE closed (weekend, {now.strftime('%A')})"
            if today in NSE_HOLIDAYS_2026:
                return False, f"NSE closed (holiday: {today})"

            t = now.time()
            if time(9, 15) <= t <= time(15, 30):
                return True, "NSE open"
            elif t < time(9, 15):
                return False, f"NSE pre-market (opens at 09:15, now {t})"
            else:
                return False, f"NSE closed (closed at 15:30, now {t})"

        if adapter_name == "memory":
            return True, "memory adapter (backtest mode — always open)"

        return False, f"unknown adapter: {adapter_name}"

    @staticmethod
    def time_until_next_open(adapter_name: str, now: Optional[datetime] = None) -> Optional[timedelta]:
        """How long until the market opens, or None if already open."""
        is_open, _ = MarketHoursChecker.is_open(adapter_name, now)
        if is_open:
            return None
        # Implementation left to specific adapters; conservative: return 1 hour
        return timedelta(hours=1)

    @staticmethod
    def get_session_window(adapter_name: str) -> MarketHoursConfig:
        """Return the bot's signal-gate / cutoff times for this market."""
        # All adapters use the same 10:00–12:00 IST window for STRATEGY PARITY
        # (NSE-equivalent times, applied uniformly so strategy logic is identical)
        return MarketHoursConfig(
            market_open=time(0, 0) if adapter_name in ("binance", "alphavantage", "memory") else time(9, 15),
            market_close=time(23, 59, 59) if adapter_name == "binance" else time(15, 30),
            signal_gate=time(10, 0),
            no_entry_after=time(12, 0),
            force_close_at=time(15, 15),
            timezone="Asia/Kolkata",
            is_24x7=(adapter_name == "binance"),
            trading_days=(
                ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"] if adapter_name == "binance"
                else ["Mon","Tue","Wed","Thu","Fri"]
            ),
        )


__all__ = ["MarketHoursChecker", "NSE_HOLIDAYS_2026"]
