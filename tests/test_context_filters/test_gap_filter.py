import unittest
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
from modules.context_filters.gap_filter import GapAlignmentFilter

class TestGapFilter(unittest.TestCase):
    
    def setUp(self):
        with open("config/context_filters.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.filter = GapAlignmentFilter(self.config, Path("data/gap_stats.joblib"))
        
    def test_micro_gap_allow(self):
        v = self.filter.evaluate(0.1, 0.1, "LONG", datetime(2023, 1, 1, 9, 30))
        self.assertEqual(v.verdict, "ALLOW")
        self.assertEqual(v.gap_category, "micro")

    def test_medium_contra_veto(self):
        # Medium Bullish gap + SHORT signal
        # Needs 50% retrace
        v = self.filter.evaluate(0.6, 0.8, "SHORT", datetime(2023, 1, 1, 9, 30), retracement_pct=0.2)
        self.assertEqual(v.verdict, "VETO")
        self.assertIn("Contra-gap needs 50% retrace", v.reasoning)
        
        # Allow if retrace is 0.6
        v2 = self.filter.evaluate(0.6, 0.8, "SHORT", datetime(2023, 1, 1, 9, 30), retracement_pct=0.6)
        self.assertEqual(v2.verdict, "ALLOW")

    def test_extreme_blackout(self):
        v = self.filter.evaluate(2.0, 2.5, "LONG", datetime(2023, 1, 1, 9, 20))
        self.assertEqual(v.verdict, "VETO")
        self.assertIn("Extreme gap blackout", v.reasoning)

if __name__ == '__main__':
    unittest.main()
