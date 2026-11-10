import unittest
import pandas as pd
import numpy as np
import yaml
from modules.smc.structure import StructureTracker

class TestStructureTracker(unittest.TestCase):
    
    def setUp(self):
        with open("config/smc.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            
    def test_choch_detection(self):
        """
        Structure test: synthetic HH-HL-HH sequence then a close below last 
        HL, assert CHoCH detected.
        """
        tracker = StructureTracker(self.config)
        dates = pd.date_range("2023-01-01 09:15", periods=100, freq="5min")
        
        # 1. Setup noise
        data = pd.DataFrame({
            'Open': [100.0] * 100, 'High': [100.0] * 100, 'Low': [100.0] * 100, 
            'Close': [100.0] * 100, 'Volume': [1000] * 100
        }, index=dates)
        
        # 2. Construct HH-HL sequence
        # bar 10: Low 90 (First Swing Low)
        # bar 20: High 110 (First Swing High)
        # bar 30: Low 95 (Higher Low)
        # bar 40: High 115 (Higher High)
        data.loc[dates[10], ['High', 'Low', 'Close']] = [91, 90, 90.5]
        data.loc[dates[20], ['High', 'Low', 'Close']] = [110, 109, 109.5]
        data.loc[dates[30], ['High', 'Low', 'Close']] = [96, 95, 95.5]
        data.loc[dates[40], ['High', 'Low', 'Close']] = [115, 114, 114.5]
        
        atr = 5.0 # Threshold = 0.5 * 5 = 2.5
        
        # Update up to bar 40 (index 40)
        for i in range(1, 42):
            state = tracker.update(data.iloc[:i], atr, [])
            
        self.assertEqual(state.last_swing_HL, 95.0)
        self.assertEqual(state.last_swing_HH, 115.0)
        
        # 3. CHoCH: Close below 95 at index 41
        data.loc[dates[41], ['High', 'Low', 'Close']] = [94, 93, 94.0]
        state = tracker.update(data.iloc[:43], atr, [])
        
        self.assertIsNotNone(state.last_CHoCH)
        self.assertEqual(state.last_CHoCH['direction'], 'BEAR')

if __name__ == '__main__':
    unittest.main()
