import pandas as pd
import numpy as np
import yaml
from typing import Dict, List, Any, Optional
from modules.intermarket.schemas import SectorVerdict
from modules.intermarket.universe_mapper import SymbolUniverseMapper

class SectorStrengthAnalyzer:
    def __init__(self, config_path: str = "config/intermarket.yaml", universe_mapper: Optional[SymbolUniverseMapper] = None):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['sector']
        self.mapper = universe_mapper or SymbolUniverseMapper()
        self.sector_ranks_history = [] # To track rotation

    def compute_rs_sector(self, sector_df: pd.DataFrame, nifty_df: pd.DataFrame) -> float:
        if sector_df is None or nifty_df is None or sector_df.empty or nifty_df.empty:
            return 0.0
        
        # rs_sector = (sector_return_since_open - nifty_return_since_open) * 100
        s_open = sector_df['open'].iloc[0]
        s_curr = sector_df['close'].iloc[-1]
        n_open = nifty_df['open'].iloc[0]
        n_curr = nifty_df['close'].iloc[-1]
        
        s_ret = (s_curr - s_open) / s_open
        n_ret = (n_curr - n_open) / n_open
        
        return (s_ret - n_ret) * 100

    def evaluate(self, symbol: str, direction: str, 
                 sector_indices: Dict[str, pd.DataFrame], 
                 nifty_df: pd.DataFrame,
                 universe_snapshot: Dict[str, Any]) -> SectorVerdict:
        
        target_sector = self.mapper.get_sector(symbol)
        
        # 1. Rank all sectors
        rs_values = {}
        for sector_name, df in sector_indices.items():
            rs_values[sector_name] = self.compute_rs_sector(df, nifty_df)
            
        sorted_sectors = sorted(rs_values.items(), key=lambda x: x[1], reverse=True)
        ranks = {name: i+1 for i, (name, val) in enumerate(sorted_sectors)}
        
        total = len(sorted_sectors)
        target_rank = ranks.get(target_sector, total)
        target_rs = rs_values.get(target_sector, 0.0)
        
        # 2. Classification
        classification = "NEUTRAL"
        top_quartile_threshold = total * self.config['leaders_quartile']
        bottom_quartile_threshold = total * (1 - self.config['laggards_quartile'])
        
        if target_rank <= top_quartile_threshold:
            classification = "LEADERS"
        elif target_rank > bottom_quartile_threshold:
            classification = "LAGGARDS"

        # 3. Score Delta
        score_delta = 0.0
        if direction == "LONG":
            if classification == "LEADERS": score_delta += self.config['score_deltas']['aligned_leader_long']
            elif classification == "LAGGARDS": score_delta += self.config['score_deltas']['contra_laggard']
        else: # SHORT
            if classification == "LAGGARDS": score_delta += self.config['score_deltas']['aligned_laggard_short']
            elif classification == "LEADERS": score_delta += self.config['score_deltas']['contra_leader']

        # 4. Rotation (Stub for now)
        rotation_event = False

        # 5. Peer Breadth
        peers = self.mapper.peers_in_sector(symbol, top_n=self.config['peer_breadth_peers_n'])
        aligned_count = 0
        for p in peers:
            p_snap = universe_snapshot.get(p)
            if p_snap:
                p_open = p_snap.get('open')
                p_close = p_snap.get('close')
                if p_open and p_close:
                    p_dir = "LONG" if p_close > p_open else "SHORT"
                    if p_dir == direction:
                        aligned_count += 1
        
        if aligned_count >= 4:
            score_delta += self.config['peer_breadth_score']['four_five']
        elif aligned_count >= 3:
            score_delta += self.config['peer_breadth_score']['three_five']
        elif aligned_count <= 2 and direction == "SHORT":
             score_delta += self.config['peer_breadth_score']['two_or_less_contra']

        reasoning = f"Sector: {target_sector} | Rank: {target_rank}/{total} ({classification}) | RS: {target_rs:.2f}% | Peers: {aligned_count}/{len(peers)}"
        
        return SectorVerdict(
            sector=target_sector,
            sector_rank=target_rank,
            total_sectors=total,
            rs_value_pct=target_rs,
            classification=classification,
            rotation_event=rotation_event,
            peer_breadth_aligned=aligned_count,
            score_delta=score_delta,
            reasoning=reasoning
        )
