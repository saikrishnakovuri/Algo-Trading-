import unittest
from pathlib import Path
from datetime import date, time
from modules.context_filters.calendar import TradingCalendar

class TestTradingCalendar(unittest.TestCase):
    
    def setUp(self):
        self.cal = TradingCalendar(Path("config/trading_calendar.yaml"))
        
    def test_holiday_detection(self):
        # Jan 26, 2026 is Republic Day (Monday)
        self.assertFalse(self.cal.is_trading_day(date(2026, 1, 26)))
        # Jan 27, 2026 should be a trading day
        self.assertTrue(self.cal.is_trading_day(date(2026, 1, 27)))

    def test_weekly_expiry(self):
        # 2026-04-16 is a Thursday
        self.assertTrue(self.cal.is_weekly_expiry(date(2026, 4, 16)))
        # 2026-04-15 is a Wednesday
        self.assertFalse(self.cal.is_weekly_expiry(date(2026, 4, 15)))

    def test_monthly_expiry(self):
        # April 2026 Thursdays: 2, 9, 16, 23, 30.
        # But April 2 is Good Friday (Holiday in my yaml, wait, I put 2026-04-02 as Good Friday)
        # 2026-04-30 is the last Thursday.
        self.assertTrue(self.cal.is_monthly_expiry(date(2026, 4, 30)))
        self.assertFalse(self.cal.is_monthly_expiry(date(2026, 4, 23)))

    def test_event_lookup(self):
        events = self.cal.scheduled_events(date(2026, 2, 1))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Union Budget")

if __name__ == '__main__':
    unittest.main()
