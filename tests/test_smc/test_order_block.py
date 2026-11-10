import unittest
import pandas as pd
import numpy as np
import yaml
from modules.smc.order_block import OrderBlockDetector

class TestOrderBlockDetector(unittest.TestCase):
    
    def setUp(self):
        with open("config/smc.yaml", "r") as f:
            self.config = yaml.safe_load(f)
            
    def test_bullish_ob_detection(self):
        """
        OB test: construct 1 bearish candle followed by 3 strong bull candles, 
        assert bullish OB detected with correct bounds and strength.
        """
        detector = OrderBlockDetector(self.config, "5m")
        
        # 1. Setup 20 bars of noise
        dates = pd.date_range("2023-01-01 09:15", periods=30, freq="5min")
        data = pd.DataFrame({
            'Open': [100.0] * 30, 'High': [101.0] * 30, 'Low': [99.0] * 30, 
            'Close': [100.0] * 30, 'Volume': [1000] * 30
        }, index=dates)
        
        # 2. Add OB candidate at index 20 (Bearish)
        data.loc[dates[20]] = [100.0, 100.5, 98.0, 98.5, 1000] 
        
        # 3. Add Displacement (3 Bullish candles)
        # Total range should be >= 1.5 * ATR. ATR of noise is ~2.0. Min range ~3.0.
        data.loc[dates[21]] = [98.5, 100.0, 98.5, 100.0, 2000]
        data.loc[dates[22]] = [100.0, 102.0, 100.0, 102.0, 2000]
        data.loc[dates[23]] = [102.0, 104.0, 102.0, 104.0, 2000]
        
        # Update detector up to index 24 (which means df length 24)
        atr = 2.0
        obs = []
        for i in range(1, 25):
            obs = detector.update(data.iloc[:i], atr)
            
        # OB should be detected at idx 20
        self.assertEqual(len(obs), 1)
        ob = obs[0]
        self.assertEqual(ob.direction, "BULL")
        self.assertEqual(ob.ob_high, 100.5)
        self.assertEqual(ob.ob_low, 98.0)
        self.assertEqual(ob.status, "UNMITIGATED")
        
    def test_ob_mitigation(self):
        detector = OrderBlockDetector(self.config, "5m")
        dates = pd.date_range("2023-01-01 09:15", periods=30, freq="5min")
        data = pd.DataFrame({
            'Open': [100.0] * 30, 'High': [101.0] * 30, 'Low': [99.0] * 30, 
            'Close': [100.0] * 30, 'Volume': [1000] * 30
        }, index=dates)
        
        atr = 1.0
        # Create OB
        data.loc[dates[5]] = [100.0, 100.5, 99.0, 99.5, 1000] # Bearish OB
        data.loc[dates[6]] = [99.5, 101.0, 99.5, 101.0, 2000]
        data.loc[dates[7]] = [101.0, 102.5, 101.0, 102.5, 2000]
        data.loc[dates[8]] = [102.5, 104.0, 102.5, 104.0, 2000]
        
        for i in range(1, 10):
            detector.update(data.iloc[:i], atr)
            
        self.assertEqual(len(detector.obs), 1)
        self.assertEqual(detector.obs[0].status, "UNMITIGATED")
        
        # Mitigate Partial: touch high (100.5)
        data.loc[dates[10]] = [104.0, 104.0, 100.0, 101.0, 1000]
        detector.update(data.iloc[:11], atr)
        self.assertEqual(detector.obs[0].status, "MITIGATED_PARTIAL")
        self.assertEqual(detector.obs[0].touches, 1)
        
        # Mitigate Full: close beyond midpoint (99.75)
        data.loc[dates[11]] = [101.0, 101.0, 99.5, 99.6, 1000]
        detector.update(data.iloc[:12], atr)
        self.assertEqual(detector.obs[0].status, "MITIGATED_FULL")

if __name__ == '__main__':
    unittest.main()
