from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import pandas as pd

@dataclass
class IndexContext:
    symbol: str                           # "NIFTY" | "BANKNIFTY"
    ohlcv_5m: pd.DataFrame
    ohlcv_15m: pd.DataFrame
    session_open: float
    regime: str                           # regime computed on index itself

@dataclass
class UniverseSnapshot:
    """Current state of all tracked stocks for breadth + RS ranking."""
    timestamp: datetime
    symbol_snapshots: Dict[str, Dict[str, Any]]     # {symbol: {close, open, vwap, session_return, vol, high, low, ...}}

@dataclass
class CrossAssetSnapshot:
    usdinr: Dict[str, Any]                          # {'close','open','session_return','trend_5m'}
    crude: Dict[str, Any]
    gold: Dict[str, Any]
    india_vix: Dict[str, Any]                       # includes vol_regime_shift flag
    sgx_nifty: Dict[str, Any]                       # includes premium_vs_spot

@dataclass
class IndexAlignmentVerdict:
    nifty_state: str
    banknifty_state: Optional[str]
    alignment: str  # "ALIGNED_STRONG"|"ALIGNED"|"NEUTRAL"|"CONTRA"|"CONTRA_STRONG"
    score_delta: float
    veto: bool
    override_applied: Optional[str]
    reasoning: str

@dataclass
class SectorVerdict:
    sector: str
    sector_rank: int
    total_sectors: int
    rs_value_pct: float
    classification: str # "LEADERS"|"NEUTRAL"|"LAGGARDS"
    rotation_event: bool
    peer_breadth_aligned: int        # out of 5
    score_delta: float
    reasoning: str

@dataclass
class RelativeStrengthVerdict:
    rs_values: Dict[str, float] # {15m: float, 60m: float, session: float, 5d: float}
    rs_percentiles: Dict[str, float]
    classification: str
    rs_momentum_aligned: bool
    score_delta: float
    veto: bool
    reasoning: str

@dataclass
class BreadthVerdict:
    regime: str
    adr: float
    up_vol_ratio: float
    pct_above_vwap: float
    divergence: Optional[str]
    score_delta: float
    reasoning: str

@dataclass
class CrossAssetVerdict:
    relevant_assets: List[str]       # which assets applied to this symbol
    asset_states: Dict[str, Any]
    score_delta: float
    reasoning: str

@dataclass
class GlobalRiskVerdict:
    sentiment: str
    global_indices_snapshot: Dict[str, float]
    fii_flow_prior_day: float
    dii_flow_prior_day: float
    fii_dii_divergence: bool
    score_delta: float
    veto: bool
    reasoning: str

@dataclass
class IntermarketVerdict:
    allow: bool
    raw_combined_delta: float
    regime_weighted_delta: float
    final_delta: float                    # after setup + window weighting
    veto_reasons: List[str]
    sub_verdicts: Dict[str, Any]          # all six individual verdicts
    reasoning: str
    evaluated_at: datetime
