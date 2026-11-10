import unittest
import pandas as pd
import numpy as np
import yaml
from modules.smc.fair_value_gap import FairValueGapDetector

class TestFairValueGapDetector(unittest.TestCase):
    
    def setUp(self):
        with open("config/smc.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            
    def test_bullish_fvg_detection(self):
        """
        FVG test: 3-candle bullish gap pattern, assert detection.
        """
        detector = FairValueGapDetector(self.config, "5m")
        dates = pd.date_range("2023-01-01 09:15", periods=5, freq="5min")
        
        # c1 high < c3 low
        data = pd.DataFrame({
            'High': [100.0, 105.0, 110.0, 100.0, 100.0],
            'Low': [95.0, 101.0, 106.0, 100.0, 100.0],
            'Open': [98.0, 102.0, 107.0, 100.0, 100.0],
            'Close': [99.0, 104.0, 109.0, 100.0, 100.0]
        }, index=dates)
        
        atr = 1.0
        # Update up to c3 (idx 2)
        fvgs = detector.update(data.iloc[:3], atr)
        
        self.assertEqual(len(fvgs), 1)
        f = fvgs[0]
        self.assertEqual(f.direction, "BULL")
        self.assertEqual(f.fvg_low, 100.0) # c1.high
        self.assertEqual(f.fvg_high, 106.0) # c3.low
        self.assertEqual(f.status, "OPEN")
        
        # Partially fill: low reached 103
        data.loc[dates[3], 'Low'] = 103.0
        detector.update(data.iloc[:4], atr)
        self.assertEqual(detector.fvgs[0].status, "PARTIALLY_FILLED")
        # fill = (106 - 103) / 6 = 3/6 = 0.5
        self.assertAlmostEqual(detector.fvgs[0].fill_pct, 0.5)
        
        # Fully fill: low reached 99
        data.loc[dates[4], 'Low'] = 99.0
        detector.update(data.iloc[:5], atr)
        self.assertEqual(detector.fvgs[0].status, "FILLED")
        self.assertEqual(detector.fvgs[0].fill_pct, 1.0)

if __name__ == '__main__':
    unittest.main()
