import unittest
import pandas as pd
import numpy as np
import yaml
from modules.vp_avwap.anchored_vwap import AnchoredVWAPEngine

class TestAnchoredVWAPEngine(unittest.TestCase):
    
    def setUp(self):
        with open("config/vp_avwap.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.engine = AnchoredVWAPEngine(self.config)
        
    def test_linear_price_constant_volume(self):
        """
        AVWAP with constant volume and linear price -> assert AVWAP equals simple mean.
        """
        n = 100
        data = pd.DataFrame({
            'High': np.linspace(100, 110, n),
            'Low': np.linspace(100, 110, n),
            'Close': np.linspace(100, 110, n),
            'Volume': [100] * n
        })
        
        vwap_res = self.engine._calculate_vwap(data)
        
        # Simple mean of [100...110] is 105
        self.assertAlmostEqual(vwap_res['value'], 105.0, delta=0.5)
        
    def test_anchors_detection(self):
        # Create 1m data over 2 days
        dates = pd.date_range("2023-01-01 09:15", periods=500, freq="1min")
        data = pd.DataFrame({
            'Open': [100.0] * 500,
            'High': [101.0] * 500,
            'Low': [99.0] * 500,
            'Close': [100.0] * 500,
            'Volume': [1000] * 500
        }, index=dates)
        
        df_5m = data.resample('5min').last().dropna()
        
        # PDH = 105 on yesterday
        prior_ohlc = {'high': 105.0, 'low': 95.0, 'close': 100.0}
        
        anchors = self.engine._detect_anchors(data, prior_ohlc, df_5m, atr_5m=1.0)
        
        self.assertIn('Session_Open', anchors)
        # Since we mocked linear data, it might not find swings unless there is variation.
        # But Session_Open should always be there.

if __name__ == '__main__':
    unittest.main()
