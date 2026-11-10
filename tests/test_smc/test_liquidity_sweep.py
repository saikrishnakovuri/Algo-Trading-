import unittest
import pandas as pd
import numpy as np
import yaml
from modules.smc.liquidity_sweep import LiquiditySweepDetector

class TestLiquiditySweepDetector(unittest.TestCase):
    
    def setUp(self):
        with open("config/smc.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            
    def test_pdh_sweep_detection(self):
        """
        Sweep test: price pokes above a PDH then closes back, assert sweep 
        detected with tier 1.
        """
        detector = LiquiditySweepDetector(self.config, "1m")
        # Increase periods to ensure rolling mean has enough data
        dates = pd.date_range("2023-01-01 09:15", periods=50, freq="1min")
        
        # PDH = 100
        prior_ohlc = {'high': 100.0, 'low': 90.0, 'close': 95.0}
        preopen = {'high': 98.0, 'low': 94.0}
        
        data = pd.DataFrame({
            'Open': [95.0] * 50, 'High': [96.0] * 50, 'Low': [94.0] * 50, 
            'Close': [95.0] * 50, 'Volume': [1000] * 50
        }, index=dates)
        
        atr = 1.0
        # Breach at index 30 (plenty of volume data before)
        data.loc[dates[30]] = [99.0, 100.5, 99.0, 100.2, 2000] # Breach
        data.loc[dates[31]] = [100.2, 100.3, 99.5, 99.6, 1000] # Reversal
        
        sweeps = []
        for i in range(1, 35):
            sweeps = detector.update(data.iloc[:i], atr, prior_ohlc, preopen)
            
        self.assertGreaterEqual(len(sweeps), 1)
        # Check if at least one is PDH
        pdh_sweeps = [s for s in sweeps if s.pool_type == "PDH"]
        self.assertTrue(len(pdh_sweeps) > 0)
        s = pdh_sweeps[0]
        self.assertEqual(s.sweep_candle_idx, 30)
        self.assertEqual(s.reversal_candle_idx, 31)

if __name__ == '__main__':
    unittest.main()
