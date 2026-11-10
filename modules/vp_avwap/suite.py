import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any

from modules.vp_avwap.schemas import LevelSet, VPScoreResult, ConfluenceLevel
from modules.vp_avwap.session_profile import SessionVolumeProfile
from modules.vp_avwap.composite_profile import CompositeVolumeProfile
from modules.vp_avwap.anchored_vwap import AnchoredVWAPEngine
from modules.vp_avwap.initial_balance import InitialBalanceAnalyzer
from modules.vp_avwap.level_merger import LevelMerger
from modules.vp_avwap.scorer import VPSignalScorer

class VolumeProfileAVWAPSuite:
    """
    Orchestrates all volume and VWAP based analysis.
    """
    
    def __init__(self, config: Dict[str, Any], composite_cache_dir: Path):
        self.config = config
        self.session_profile = SessionVolumeProfile(config)
        self.composite_profile = CompositeVolumeProfile(config, str(composite_cache_dir))
        self.avwap_engine = AnchoredVWAPEngine(config)
        self.ib_analyzer = InitialBalanceAnalyzer(config)
        self.level_merger = LevelMerger(config)
        self.scorer = VPSignalScorer(config)
    
    def compute_levels(
        self,
        symbol: str,
        intraday_1m: pd.DataFrame,
        historical_1m: pd.DataFrame,
        prior_session_ohlc: Dict[str, float],
        atr_5m: float,
        tick_size: float = 0.05
    ) -> LevelSet:
        
        # 1. Session Profile
        session_vp = self.session_profile.compute(intraday_1m, atr_5m, tick_size)
        
        # 2. Composite Profiles (Load from cache if possible)
        comp_5d = self.composite_profile.load_from_cache(symbol, 5) or {}
        comp_20d = self.composite_profile.load_from_cache(symbol, 20) or {}
        
        # 3. AVWAPs
        # We need a 5m resampled version for swings
        df_5m = intraday_1m.resample('5min').last().dropna()
        avwaps = self.avwap_engine.compute_all(intraday_1m, prior_session_ohlc, df_5m, atr_5m)
        
        # 4. IB
        ib = self.ib_analyzer.compute_ib(intraday_1m)
        
        # 5. Merge all into ConfluenceLevels
        raw_list = []
        
        # From Session Profile
        if session_vp:
            raw_list.append({'price': session_vp['POC'], 'type': 'POC', 'strength': 0.8})
            raw_list.append({'price': session_vp['VAH'], 'type': 'VAH', 'strength': 0.4})
            raw_list.append({'price': session_vp['VAL'], 'type': 'VAL', 'strength': 0.4})
            for hvn in session_vp.get('HVNs', []):
                raw_list.append({'price': hvn['price'], 'type': 'HVN', 'strength': hvn['strength']})
                
        # From Composites
        if comp_5d:
            raw_list.append({'price': comp_5d['POC'], 'type': 'POC_5d', 'strength': 0.6})
        if comp_20d:
            raw_list.append({'price': comp_20d['POC'], 'type': 'POC_20d', 'strength': 0.5})
            
        # From AVWAPs
        for name, data in avwaps.items():
            raw_list.append({'price': data['value'], 'type': f'AVWAP_{name}', 'strength': 0.5})
            
        # From IB
        if ib:
            raw_list.append({'price': ib['IBH'], 'type': 'IBH', 'strength': 0.4})
            raw_list.append({'price': ib['IBL'], 'type': 'IBL', 'strength': 0.4})

        merged = self.level_merger.merge(raw_list, atr_5m)
        
        return LevelSet(
            session_vp=session_vp,
            composite_5d=comp_5d,
            composite_20d=comp_20d,
            avwaps=avwaps,
            ib=ib,
            confluence_levels=merged,
            computed_at=datetime.now()
        )
    
    def score_signal(
        self,
        signal_entry_price: float,
        signal_direction: Literal["LONG","SHORT"],
        level_set: LevelSet,
        regime: str,
        atr_5m: float
    ) -> VPScoreResult:
        return self.scorer.score(signal_entry_price, signal_direction, level_set, regime, atr_5m)
