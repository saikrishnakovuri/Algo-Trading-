import unittest
from modules.regime.rule_layer import RuleBasedClassifier

class TestRuleLayer(unittest.TestCase):
    def setUp(self):
        self.classifier = RuleBasedClassifier()

    def test_trending_high_vol(self):
        features = {
            "ADX_5m": 30, "Choppiness_5m": 30, "Hurst_exponent": 0.6, "RV_ratio": 1.5,
            "VIX_slope": 0, "Range_ratio": 1.5
        }
        decision = self.classifier.classify(features)
        self.assertEqual(decision.regime, "TRENDING_HIGH_VOL")
        self.assertTrue(decision.allow_trades)

    def test_mean_reverting(self):
        features = {
            "ADX_5m": 15, "Choppiness_5m": 45, "Hurst_exponent": 0.4, "RV_ratio": 1.0,
            "VIX_slope": 0, "Range_ratio": 1.0
        }
        decision = self.classifier.classify(features)
        self.assertEqual(decision.regime, "MEAN_REVERTING")
        self.assertTrue(decision.allow_trades)

    def test_choppy_by_indicator(self):
        features = {
            "ADX_5m": 10, "Choppiness_5m": 70, "Hurst_exponent": 0.5, "RV_ratio": 1.0,
            "VIX_slope": 0, "Range_ratio": 0.4
        }
        decision = self.classifier.classify(features)
        self.assertEqual(decision.regime, "CHOPPY_UNTRADEABLE")
        self.assertFalse(decision.allow_trades)

    def test_choppy_by_vix(self):
        features = {
            "ADX_5m": 20, "Choppiness_5m": 40, "Hurst_exponent": 0.5, "RV_ratio": 1.0,
            "VIX_slope": 20, "Range_ratio": 1.0
        }
        decision = self.classifier.classify(features)
        self.assertEqual(decision.regime, "CHOPPY_UNTRADEABLE")
        self.assertFalse(decision.allow_trades)

if __name__ == '__main__':
    unittest.main()
