from dataclasses import dataclass, field
from datetime import datetime
try:
    from typing import Dict, Any, List, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, List, Optional, Union
    Literal = Any

@dataclass
class OrderBlock:
    ob_high: float
    ob_low: float
    ob_open: float
    ob_close: float
    created_at: datetime
    timeframe: Literal["5m", "1m"]
    direction: Literal["BULL", "BEAR"]
    displacement_atr: float
    status: Literal["UNMITIGATED", "MITIGATED_PARTIAL", "MITIGATED_FULL", "INVALIDATED"]
    touches: int
    strength: float

@dataclass
class FairValueGap:
    fvg_high: float
    fvg_low: float
    created_at: datetime
    timeframe: Literal["5m", "1m"]
    direction: Literal["BULL", "BEAR"]
    gap_atr: float
    status: Literal["OPEN", "PARTIALLY_FILLED", "FILLED"]
    fill_pct: float
    strength: float

@dataclass
class LiquiditySweep:
    sweep_price: float
    pool_level: float
    sweep_candle_idx: int
    reversal_candle_idx: Optional[int]
    pool_type: Literal["PDH", "PDL", "SH", "SL", "EQH", "EQL", "PREOPEN_H", "PREOPEN_L"]
    tier: int
    timeframe: Literal["5m", "1m"]
    volume_ratio: float
    atr_penetration: float
    status: Literal["ACTIVE", "EXPIRED"]

@dataclass
class StructureState:
    current_state: Literal["UPTREND", "DOWNTREND", "TRANSITIONING"]
    last_BOS: Optional[Dict[str, Any]] = None      # {direction, price, bar_idx, ts}
    last_CHoCH: Optional[Dict[str, Any]] = None
    last_MSS: Optional[Dict[str, Any]] = None
    last_swing_HH: Optional[float] = None
    last_swing_HL: Optional[float] = None
    last_swing_LH: Optional[float] = None
    last_swing_LL: Optional[float] = None
    breaker_blocks: List[OrderBlock] = field(default_factory=list)

@dataclass
class SMCState:
    order_blocks_5m: List[OrderBlock]
    order_blocks_1m: List[OrderBlock]
    fvgs_5m: List[FairValueGap]
    fvgs_1m: List[FairValueGap]
    active_sweeps: List[LiquiditySweep]
    structure: StructureState
    premium_discount: Dict[str, Any]                # current zone classification
    computed_at: datetime

@dataclass
class SMCScoreResult:
    raw_score: float
    regime_weighted_score: float
    tier_label: Literal["MONEY", "ELITE", "STRONG", "GOOD", "MINOR", "NONE", "PENALISED"]
    aligned_footprints: List[str]         # human readable list
    reasoning: str
