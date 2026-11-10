import unittest
import yaml
from pathlib import Path
from datetime import datetime, time
from freezegun import freeze_time
from modules.context_filters.calendar import TradingCalendar
from modules.context_filters.time_of_day_filter import TimeOfDayFilter

class TestTimeOfDayFilter(unittest.TestCase):
    
    def setUp(self):
        with open("config/context_filters.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.cal = TradingCalendar(Path("config/trading_calendar.yaml"))
        self.filter = TimeOfDayFilter(self.config, self.cal)
        
    def test_opening_burst_allow(self):
        # 09:30 on a normal Tuesday
        now = datetime(2026, 4, 7, 9, 30) 
        v = self.filter.evaluate(now, "TRAP_FADE", 15, "MEAN_REVERTING")
        self.assertEqual(v.verdict, "ALLOW")
        self.assertEqual(v.active_window, "OPENING_BURST")
        self.assertEqual(v.setup_weight_multiplier, 1.0)

    def test_opening_insufficient_bars(self):
        # 09:16 but only 1 bar
        now = datetime(2026, 4, 7, 9, 16)
        v = self.filter.evaluate(now, "TRAP_FADE", 1, "MEAN_REVERTING")
        self.assertEqual(v.verdict, "VETO")
        self.assertIn("Insufficient bars", v.reasoning)

    def test_lunch_dead_zone(self):
        # 12:15 on Tuesday
        now = datetime(2026, 4, 7, 12, 15)
        v = self.filter.evaluate(now, "TRAP_FADE", 100, "TRENDING_LOW_VOL")
        self.assertEqual(v.verdict, "ALLOW")
        self.assertEqual(v.sub_window, "lunch_dead")
        # delta should be 0.6 from config
        self.assertEqual(v.score_threshold_delta, 0.6)

    def test_expiry_restriction(self):
        # Thursday 2026-04-16, 12:45 (after 12:30 cut-off)
        now = datetime(2026, 4, 16, 12, 45)
        v = self.filter.evaluate(now, "TREND_CONTINUATION", 100, "TRENDING_HIGH_VOL")
        self.assertEqual(v.verdict, "VETO")
        self.assertEqual(v.active_window, "NO_NEW_ENTRIES")

    def test_outside_hours(self):
        now = datetime(2026, 4, 7, 16, 0)
        v = self.filter.evaluate(now, "TRAP_FADE", 100, "MEAN_REVERTING")
        self.assertEqual(v.verdict, "VETO")

if __name__ == '__main__':
    unittest.main()
