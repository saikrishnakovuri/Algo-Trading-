from dataclasses import dataclass, field
from datetime import datetime, time
try:
    from typing import Dict, Any, List, Optional, Union
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, List, Optional, Union
    Literal = Any

@dataclass
class ChopVerdict:
    verdict: Literal["ALLOW", "WARN", "VETO"]
    chop_score: float
    metrics: Dict[str, float] # {"RCR": float, "BBR": float, "ZZD": int, "VD": float}
    regime_adjusted_threshold: float
    reasoning: str

@dataclass
class TimeOfDayVerdict:
    verdict: Literal["ALLOW", "VETO"]
    active_window: Literal["OPENING_BURST", "TREND_DEVELOPMENT", "NO_NEW_ENTRIES", "LUNCH_DEAD", "EXPIRY_RESTRICTED", "EVENT_BLACKOUT"]
    sub_window: Optional[str]
    setup_weight_multiplier: float     # applied to signal score by caller
    score_threshold_delta: float       # added to adaptive_threshold
    max_concurrent_override: Optional[int]
    reasoning: str

@dataclass
class GapVerdict:
    verdict: Literal["ALLOW", "VETO"]
    gap_category: str
    gap_direction: Literal["BULL", "BEAR", "NONE"]
    gap_pct: float
    gap_atr: float
    historical_fill_probability: float
    signal_alignment: Literal["ALIGNED", "CONTRA", "NEUTRAL"]
    weight_multiplier: float           # applied to signal score by caller
    stock_vs_index_anomaly: bool
    reasoning: str

@dataclass
class AllowDecision:
    allow_trade: bool
    combined_weight_multiplier: float
    combined_threshold_delta: float
    veto_reasons: List[str]
    warnings: List[str]
    chop: ChopVerdict
    time_of_day: TimeOfDayVerdict
    gap: GapVerdict
    evaluated_at: datetime
    symbol: str

@dataclass
class Event:
    date: str
    time: str
    name: str
    blackout_pre_min: int
    blackout_post_min: int
