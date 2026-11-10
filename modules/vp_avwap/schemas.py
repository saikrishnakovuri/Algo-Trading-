from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Union
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any # Fallback for Python 3.7 if typing_extensions is not installed (though it should be)

@dataclass
class ConfluenceLevel:
    price: float
    width: float
    source_types: Set[str]
    strength: float         # 0–1
    confluence_count: int

@dataclass
class LevelSet:
    session_vp: Dict[str, Any]        # POC, VAH, VAL, HVNs, LVNs, dPOC, dPOC_history
    composite_5d: Dict[str, Any]
    composite_20d: Dict[str, Any]
    avwaps: Dict[str, Dict[str, float]] # {anchor_name: {'value','±1σ','±2σ','±3σ'}}
    ib: Dict[str, Any]                # IBH, IBL, IB_mid, IBE_H1..2, IBE_L1..2, day_type
    confluence_levels: List[ConfluenceLevel]
    computed_at: datetime

@dataclass
class VPScoreResult:
    raw_score: float
    regime_weighted_score: float
    nearest_confluence: Optional[ConfluenceLevel]
    distance_to_nearest_atr: float
    reasoning: str          # "Entry at POC+AVWAP_PDH+Zone_S1 (3-way confluence)"
