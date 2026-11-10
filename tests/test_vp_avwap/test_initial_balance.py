import unittest
import pandas as pd
import numpy as np
import yaml
from modules.vp_avwap.initial_balance import InitialBalanceAnalyzer

class TestInitialBalanceAnalyzer(unittest.TestCase):
    
    def setUp(self):
        with open("config/vp_avwap.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.analyzer = InitialBalanceAnalyzer(self.config)
        
    def test_basic_ib(self):
        # Create 120 bars of data (2 hours)
        dates = pd.date_range("2023-01-01 09:15", periods=120, freq="1min")
        # High=110, Low=90 for first 60 bars
        highs = [110.0] * 60 + [120.0] * 60
        lows = [90.0] * 60 + [80.0] * 60
        data = pd.DataFrame({
            'High': highs,
            'Low': lows,
            'Close': [100.0] * 120
        }, index=dates)
        
        ib = self.analyzer.compute_ib(data)
        
        self.assertEqual(ib['IBH'], 110.0)
        self.assertEqual(ib['IBL'], 90.0)
        self.assertEqual(ib['IB_range'], 20.0)
        self.assertEqual(ib['IB_mid'], 100.0)
        self.assertEqual(ib['IBE_H1'], 120.0) # 110 + 0.5 * 20
        
        # At end of 120 bars, price exceeded both sides
        self.assertEqual(ib['day_type'], "Neutral Day")

if __name__ == '__main__':
    unittest.main()
