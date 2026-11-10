import yaml
import os

class EventCalendar:
    """
    Static filter to block new trade entries on known high-impact dates.
    Uses NO_NEW_ENTRIES mode by default.
    """
    def __init__(self, config_path="config/no_trade_dates.yaml"):
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f).get('no_trade_dates', {})
        
        self.blocked_dates = self.config.get('blocked_dates', {})
        self.earnings_blackout = self.config.get('earnings_blackout', {})
        self.action = self.config.get('action', "NO_NEW_ENTRIES")

    def is_blocked_date(self, date_str: str) -> bool:
        """Checks if the entire date is in the global blocklist."""
        return date_str in self.blocked_dates

    def get_reason(self, date_str: str) -> str:
        """Returns the reason for blocking the date."""
        return self.blocked_dates.get(date_str, "Scheduled High Volatility Event")

    def is_symbol_blocked(self, symbol: str, date_str: str) -> bool:
        """Checks if a specific symbol is in an earnings blackout period."""
        blackout_dates = self.earnings_blackout.get(symbol, [])
        return date_str in blackout_dates

    def should_allow_entries(self, date_str: str) -> bool:
        """High-level check for the trading loop."""
        if self.is_blocked_date(date_str):
            return False
        return True
