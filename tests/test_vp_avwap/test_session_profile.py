import unittest
import pandas as pd
import numpy as np
import yaml
from modules.vp_avwap.session_profile import SessionVolumeProfile

class TestSessionVolumeProfile(unittest.TestCase):
    
    def setUp(self):
        with open("config/vp_avwap.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.vp = SessionVolumeProfile(self.config)
        
    def test_obvious_poc(self):
        """
        Synthetic OHLCV with obvious POC (all volume at one price).
        """
        # All bars have the same Close, and 100% volume is at Close (in our 70/20/10 model)
        # To make it 100%, we make High=Low=Close.
        data = pd.DataFrame({
            'High': [100.0] * 10,
            'Low': [100.0] * 10,
            'Close': [100.0] * 10,
            'Open': [100.0] * 10,
            'Volume': [1000] * 10
        })
        
        # ATR=0 implies bin_size = tick_size * 2 = 0.1
        profile = self.vp.compute(data, atr_5m=0.0, tick_size=0.05)
        
        # POC should be around 100.0
        self.assertAlmostEqual(profile['POC'], 100.0, delta=0.1)
        self.assertEqual(profile['total_volume'], 10000)

    def test_value_area_uniform(self):
        """
        Uniform distribution: VAH/VAL should split symmetrically.
        """
        # Prices from 100 to 110, volume 100 at each price point
        prices = np.arange(100, 110, 1)
        data = pd.DataFrame({
            'High': prices,
            'Low': prices,
            'Close': prices,
            'Open': prices,
            'Volume': [100] * len(prices)
        })
        
        profile = self.vp.compute(data, atr_5m=2.0, tick_size=0.05)
        
        # Target VA = 70% of 1000 = 700.
        # POC will be one of the middle ones.
        # VA should cover roughly 7 out of 10 bins.
        self.assertLess(profile['VAL'], profile['POC'])
        self.assertGreater(profile['VAH'], profile['POC'])
        
        # Width should be roughly 70% of total range
        total_range = 10.0
        va_width = profile['VAH'] - profile['VAL']
        self.assertAlmostEqual(va_width, total_range * 0.7, delta=2.0)

if __name__ == '__main__':
    unittest.main()
