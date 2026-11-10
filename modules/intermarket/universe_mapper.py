import yaml
import os
import pandas as pd
from typing import Dict, List, Set, Optional, Any

class SymbolUniverseMapper:
    """
    Loads universe metadata: symbol -> sector -> industry -> index membership.
    """
    def __init__(self, config_path: str = "config/universe.yaml"):
        self.config_path = config_path
        self.mappings: Dict[str, Any] = {}
        self.beta_matrix: Dict[str, float] = {}
        self.load_mappings()
        self.load_beta_matrix()

    def load_mappings(self):
        if not os.path.exists(self.config_path):
            return
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            self.mappings = data.get('universe', {}).get('mappings', {})
            self.default_beta = data.get('universe', {}).get('default_beta', 1.0)

    def load_beta_matrix(self, matrix_path: str = "data/beta_matrix.csv"):
        """Loads calculated beta values from disk."""
        if os.path.exists(matrix_path):
            df = pd.read_csv(matrix_path, index_col=0)
            self.beta_matrix = df['beta'].to_dict()
        else:
            # Fallback to base_beta from mappings
            for sym, meta in self.mappings.items():
                self.beta_matrix[sym] = meta.get('beta_base', self.default_beta)

    def get_sector(self, symbol: str) -> str:
        return self.mappings.get(symbol, {}).get('sector', 'UNKNOWN')

    def get_industry(self, symbol: str) -> str:
        return self.mappings.get(symbol, {}).get('industry', 'UNKNOWN')

    def get_beta(self, symbol: str) -> float:
        return self.beta_matrix.get(symbol, self.mappings.get(symbol, {}).get('beta_base', self.default_beta))

    def get_cross_asset_tags(self, symbol: str) -> Set[str]:
        return set(self.mappings.get(symbol, {}).get('tags', []))

    def get_indices(self, symbol: str) -> List[str]:
        return self.mappings.get(symbol, {}).get('indices', [])

    def peers_in_sector(self, symbol: str, top_n: int = 5) -> List[str]:
        target_sector = self.get_sector(symbol)
        if target_sector == 'UNKNOWN':
            return []
        
        peers = [s for s, m in self.mappings.items() if m.get('sector') == target_sector and s != symbol]
        # In production, we'd sort by turnover. For now, returning alphabetical peers.
        return sorted(peers)[:top_n]

    def get_all_symbols(self) -> List[str]:
        return list(self.mappings.keys())
