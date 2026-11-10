import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from modules.intermarket.schemas import IntermarketVerdict, IndexContext, UniverseSnapshot, CrossAssetSnapshot, GlobalRiskVerdict
from modules.intermarket.universe_mapper import SymbolUniverseMapper
from modules.intermarket.index_alignment import IndexAlignmentChecker
from modules.intermarket.sector_strength import SectorStrengthAnalyzer
from modules.intermarket.relative_strength import RelativeStrengthScorer
from modules.intermarket.breadth import BreadthEngine
from modules.intermarket.cross_asset import CrossAssetContextEngine
from modules.intermarket.global_risk import GlobalRiskContext
from modules.intermarket.aggregator import IntermarketAggregator

class IntermarketRelativeStrengthEngine:
    def __init__(self, config_path: str = "config/intermarket.yaml"):
        self.config_path = config_path
        self.mapper = SymbolUniverseMapper()
        
        self.index_checker = IndexAlignmentChecker(config_path, self.mapper)
        self.sector_analyzer = SectorStrengthAnalyzer(config_path, self.mapper)
        self.rs_scorer = RelativeStrengthScorer(config_path, self.mapper)
        self.breadth_engine = BreadthEngine(config_path)
        self.cross_asset_engine = CrossAssetContextEngine(config_path, self.mapper)
        self.global_risk_engine = GlobalRiskContext(config_path)
        self.aggregator = IntermarketAggregator(config_path)

    def evaluate(
        self,
        symbol: str,
        candidate_direction: Literal["LONG", "SHORT"],
        setup_type: str,
        active_window: str,
        regime: str,
        smc_tier: str,
        now_ist: datetime,
        nifty_ctx: IndexContext,
        sector_indices: Dict[str, pd.DataFrame],
        stock_ohlcv_session: pd.DataFrame,
        universe_snapshot: UniverseSnapshot,
        cross_assets: CrossAssetSnapshot,
        global_ctx: Optional[GlobalRiskVerdict] = None,
        banknifty_ctx: Optional[IndexContext] = None
    ) -> IntermarketVerdict:
        
        # 1. Individual evaluations
        sub_verdicts = {}
        
        sub_verdicts['index'] = self.index_checker.evaluate(
            symbol, candidate_direction, nifty_ctx, banknifty_ctx, smc_tier
        )

        nifty_ohlcv_5m = nifty_ctx.ohlcv_5m if nifty_ctx is not None else None

        sub_verdicts['sector'] = self.sector_analyzer.evaluate(
            symbol, candidate_direction, sector_indices, nifty_ohlcv_5m, universe_snapshot.symbol_snapshots
        )

        sub_verdicts['rs'] = self.rs_scorer.evaluate(
            symbol, candidate_direction, stock_ohlcv_session, nifty_ohlcv_5m, universe_snapshot, smc_tier
        )
        sub_verdicts['breadth'] = self.breadth_engine.evaluate(
            candidate_direction, universe_snapshot, symbol
        )
        
        sub_verdicts['cross_asset'] = self.cross_asset_engine.evaluate(
            symbol, candidate_direction, cross_assets
        )
        
        if global_ctx:
            sub_verdicts['global_risk'] = global_ctx
            
        # 2. Aggregation
        return self.aggregator.aggregate(
            sub_verdicts, regime, setup_type, active_window
        )
