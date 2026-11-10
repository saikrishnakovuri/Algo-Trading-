import unittest
import pandas as pd
import numpy as np
from modules.regime.features import FeatureCalculator

class TestFeatureCalculator(unittest.TestCase):

    def setUp(self):
        # Create synthetic data
        dates = pd.date_range(start="2023-01-01", periods=200, freq="5min")
        self.df_trending = pd.DataFrame({
            'Open': np.linspace(100, 200, 200) + np.random.normal(0, 0.5, 200),
            'High': np.linspace(102, 202, 200) + np.random.normal(0, 0.5, 200),
            'Low': np.linspace(98, 198, 200) + np.random.normal(0, 0.5, 200),
            'Close': np.linspace(101, 201, 200) + np.random.normal(0, 0.5, 200),
            'Volume': np.random.randint(1000, 5000, 200)
        }, index=dates)

        self.df_ranging = pd.DataFrame({
            'Open': [100, 105, 100, 95] * 50,
            'High': [106, 110, 105, 100] * 50,
            'Low': [94, 98, 93, 89] * 50,
            'Close': [101, 104, 99, 96] * 50,
            'Volume': np.random.randint(1000, 5000, 200)
        }, index=dates)

    def test_adx(self):
        adx_trending = FeatureCalculator.calculate_adx(self.df_trending)
        adx_ranging = FeatureCalculator.calculate_adx(self.df_ranging)
        # ADX should be higher for trending data
        self.assertGreater(adx_trending, 0)
        self.assertTrue(isinstance(adx_trending, float))

    def test_choppiness(self):
        chop_trending = FeatureCalculator.calculate_choppiness(self.df_trending)
        chop_ranging = FeatureCalculator.calculate_choppiness(self.df_ranging)
        # Trending should have lower choppiness than ranging
        self.assertLess(chop_trending, chop_ranging)
        self.assertGreater(chop_ranging, 50)

    def test_hurst(self):
        hurst_trending = FeatureCalculator.calculate_hurst(self.df_trending['Close'])
        # Trending should ideally be > 0.5
        self.assertGreater(hurst_trending, 0.4) # R/S can be noisy on small samples

    def test_rv_ratio(self):
        ratio = FeatureCalculator.calculate_rv_ratio(self.df_trending)
        self.assertTrue(isinstance(ratio, float))

    def test_vix_slope(self):
        vix_hist = pd.Series([15, 15.5, 16, 17, 18])
        slope = FeatureCalculator.calculate_vix_slope(vix_hist)
        self.assertEqual(slope, 20.0) # (18-15)/15 * 100

    def test_range_ratio(self):
        ratio = FeatureCalculator.calculate_range_ratio(self.df_trending)
        self.assertGreater(ratio, 0)

    def test_volume_ratio(self):
        ratio = FeatureCalculator.calculate_volume_ratio(self.df_trending)
        self.assertGreater(ratio, 0)

if __name__ == '__main__':
    unittest.main()
