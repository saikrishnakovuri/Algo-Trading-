import yaml
import pandas as pd
from pathlib import Path
from datetime import date, time, datetime, timedelta
from typing import List, Dict, Any, Optional
from modules.context_filters.schemas import Event

class TradingCalendar:
    """
    Loads NSE holiday list, expiry schedule, event schedule.
    """
    
    def __init__(self, yaml_path: Path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        self.holidays = {datetime.strptime(h['date'], "%Y-%m-%d").date() for h in self.config.get('holidays', [])}
        self.expiry_config = self.config.get('weekly_expiry', {'day_of_week': 'THU', 'shift_on_holiday': 'PREVIOUS'})
        self.monthly_expiry_end = time.fromisoformat(self.config.get('monthly_expiry_override_end_time', "13:00:00"))
        
        self.events = [Event(**e) for e in self.config.get('scheduled_events', [])]

        # Load local stock-specific event registry
        self.stock_events = {}
        events_file = Path("config/events.yaml")
        if events_file.exists():
            with open(events_file, 'r') as f:
                evt_data = yaml.safe_load(f)
                if evt_data and 'events' in evt_data:
                    for item in evt_data['events']:
                        sym = item['symbol']
                        if sym not in self.stock_events:
                            self.stock_events[sym] = []
                        self.stock_events[sym].append(item['date'])

    def is_trading_day(self, d: date) -> bool:
        """Checks if a given date is a trading day (not weekend or holiday)."""
        if d.weekday() >= 5: # Saturday=5, Sunday=6
            return False
        if d in self.holidays:
            return False
        return True

    def is_weekly_expiry(self, d: date) -> bool:
        """
        Checks if d is a weekly expiry day.
        Logic: Thursday is usually expiry. If Thursday is holiday, it shifts to Wed.
        """
        if not self.is_trading_day(d):
            return False
            
        # Target day of week (e.g. 3 for Thursday)
        target_dow = 3 # default THU
        dow_map = {'MON':0, 'TUE':1, 'WED':2, 'THU':3, 'FRI':4}
        target_dow = dow_map.get(self.expiry_config['day_of_week'], 3)
        
        # If today is the target day of week, it's likely expiry unless shifted
        if d.weekday() == target_dow:
            return True
            
        # Check if today is a shifted expiry (e.g. Wednesday because Thursday is holiday)
        if self.expiry_config['shift_on_holiday'] == 'PREVIOUS':
            # Is tomorrow the target day and a holiday?
            tomorrow = d + timedelta(days=1)
            if tomorrow.weekday() == target_dow and tomorrow in self.holidays:
                return True
                
        return False

    def is_monthly_expiry(self, d: date) -> bool:
        """Checks if d is the LAST expiry of the month."""
        if not self.is_weekly_expiry(d):
            return False
            
        # Check all subsequent days in the month
        curr = d + timedelta(days=1)
        while curr.month == d.month:
            if self.is_weekly_expiry(curr):
                return False
            curr += timedelta(days=1)
        return True

    def scheduled_events(self, d: date) -> List[Event]:
        """Returns list of events scheduled for date d."""
        d_str = d.strftime("%Y-%m-%d")
        return [e for e in self.events if e.date == d_str]

    def adjusted_end_time(self, d: date) -> time:
        """Returns session end time (usually 13:30 for bot, but 13:00 on monthly)."""
        if self.is_monthly_expiry(d):
            return self.monthly_expiry_end
        return time(13, 30)

    def stock_event_today(self, symbol: str, backtest_mode: bool = False) -> bool:
        """
        Checks if a specific stock has an event (earnings, etc.) today.
        Uses the local registry in config/events.yaml.
        """
        if backtest_mode:
            return False
            
        today_str = date.today().strftime("%Y-%m-%d")
        
        # Check local registry
        if symbol in self.stock_events:
            if today_str in self.stock_events[symbol]:
                print(f"🛡️ EVENT ALERT: {symbol} has a scheduled event today ({today_str}). Vetoing trades.")
                return True
                
        return False
