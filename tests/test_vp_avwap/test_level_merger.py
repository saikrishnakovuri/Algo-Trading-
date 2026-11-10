import unittest
import yaml
from modules.vp_avwap.level_merger import LevelMerger

class TestLevelMerger(unittest.TestCase):
    
    def setUp(self):
        with open("config/vp_avwap.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        self.merger = LevelMerger(self.config)
        
    def test_clustering(self):
        # ATR=10. Tolerance = 0.15 * 10 = 1.5
        atr_5m = 10.0
        raw = [
            {'price': 100.0, 'type': 'POC', 'strength': 0.8},
            {'price': 101.0, 'type': 'AVWAP_Session', 'strength': 0.5},
            {'price': 105.0, 'type': 'VAH', 'strength': 0.4}
        ]
        
        merged = self.merger.merge(raw, atr_5m)
        
        # 100 and 101 should cluster (diff 1.0 <= 1.5)
        # 105 should be separate
        self.assertEqual(len(merged), 2)
        
        # Cluster 1 (100, 101)
        c1 = [c for c in merged if c.confluence_count == 2][0]
        self.assertIn('POC', c1.source_types)
        self.assertIn('AVWAP_Session', c1.source_types)
        # Weighted avg: (100*0.8 + 101*0.5) / 1.3 = 100.38
        self.assertAlmostEqual(c1.price, 100.38, delta=0.1)
        self.assertEqual(c1.strength, 1.0) # 0.8 + 0.5 = 1.3, capped at 1.0

if __name__ == '__main__':
    unittest.main()
