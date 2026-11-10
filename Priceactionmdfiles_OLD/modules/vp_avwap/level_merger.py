import numpy as np
from typing import List, Dict, Any, Set
from modules.vp_avwap.schemas import ConfluenceLevel

class LevelMerger:
    """
    Clusters levels from different sources into unified ConfluenceLevels.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['merger']
        self.cluster_dist_mult = self.config.get('cluster_distance_atr', 0.15)
        
    def merge(self, raw_levels: List[Dict[str, Any]], atr_5m: float) -> List[ConfluenceLevel]:
        """
        raw_levels: list of {'price': float, 'type': str, 'strength': float}
        """
        if not raw_levels:
            return []
            
        # 1. Sort by price
        sorted_levels = sorted(raw_levels, key=lambda x: x['price'])
        
        clusters = []
        if not sorted_levels: return []
        
        current_cluster = [sorted_levels[0]]
        tolerance = self.cluster_dist_mult * atr_5m
        
        for i in range(1, len(sorted_levels)):
            if sorted_levels[i]['price'] - current_cluster[-1]['price'] <= tolerance:
                current_cluster.append(sorted_levels[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [sorted_levels[i]]
        clusters.append(current_cluster)
        
        # 2. Process clusters into ConfluenceLevels
        confluence_levels = []
        for cluster in clusters:
            prices = [l['price'] for l in cluster]
            strengths = [l['strength'] for l in cluster]
            types = {l['type'] for l in cluster}
            
            # Weighted average price by strength
            avg_price = np.average(prices, weights=strengths) if sum(strengths) > 0 else np.mean(prices)
            width = max(prices) - min(prices)
            
            # Unified strength: sum capped at 1.0
            total_strength = min(1.0, sum(strengths))
            
            confluence_levels.append(ConfluenceLevel(
                price=round(avg_price, 2),
                width=round(width, 2),
                source_types=types,
                strength=round(total_strength, 2),
                confluence_count=len(types)
            ))
            
        return sorted(confluence_levels, key=lambda x: x.strength, reverse=True)
