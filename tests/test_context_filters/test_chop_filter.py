import unittest
import pandas as pd
import numpy as np
import yaml
from modules.context_filters.chop_filter import ChopFilter

class TestChopFilter(unittest.TestCase):
    
    def setUp(self):
        with open("config/context_filters.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.filter = ChopFilter(self.config)
        
    def test_flat_range_veto(self):
        """Synthetic flat-range OHLCV -> chop_score >= 0.60, VETO."""
        dates = pd.date_range("2023-01-01 09:15", periods=15, freq="5min")
        # Very tight range, wicky bars, frequent flips, flat volume
        data = pd.DataFrame({
            'Open': [100.0, 100.1] * 7 + [100.0],
            'High': [100.2] * 15,
            'Low': [99.8] * 15,
            'Close': [100.1, 100.0] * 7 + [100.1],
            'Volume': [1000] * 15
        }, index=dates)
        
        atr = 2.0 # rcr = (100.2-99.8)/2 = 0.2 < 0.7 -> M1 choppy
        # bbr = mean(|0.1|/0.4) = 0.25 < 0.35 -> M2 choppy
        # zzd = many flips -> M3 choppy
        # vd = 0 < 0.25 -> M4 choppy
        
        verdict = self.filter.evaluate(data, atr, "TRENDING_LOW_VOL")
        self.assertEqual(verdict.verdict, "VETO")
        self.assertGreaterEqual(verdict.chop_score, 0.6)

    def test_trending_allow(self):
        """Trending series with 2-ATR range -> chop_score < 0.40, ALLOW."""
        dates = pd.date_range("2023-01-01 09:15", periods=15, freq="5min")
        # Wide range, solid bodies, no flips, spiking volume
        prices = np.linspace(100, 110, 15)
        data = pd.DataFrame({
            'Open': prices - 0.5,
            'High': prices + 0.5,
            'Low': prices - 1.0,
            'Close': prices + 0.2,
            'Volume': [1000, 5000] * 7 + [1000]
        }, index=dates)
        
        atr = 2.0 # rcr = 11.5 / 2 = 5.75 > 0.7 -> M1 active
        # bbr = mean(0.7/1.5) = 0.46 > 0.35 -> M2 active
        # zzd = 0 -> M3 active
        
        verdict = self.filter.evaluate(data, atr, "TRENDING_HIGH_VOL")
        self.assertEqual(verdict.verdict, "ALLOW")
        self.assertLess(verdict.chop_score, 0.4)

if __name__ == '__main__':
    unittest.main()
