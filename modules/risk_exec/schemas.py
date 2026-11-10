from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
try:
    from typing_extensions import Literal
except ImportError:
    Literal = Any

@dataclass
class SizingDecision:
    shares: int
    final_risk_pct: float
    risk_amount: float
    components: Dict[str, float]  # {base: float, kelly_mult: float, vol_mult: float}
    constraints_hit: List[str]
    reasoning: str

@dataclass
class SLDecision:
    sl_price: float
    per_share_risk: float
    candidates: Dict[str, float]  # {zone: float, structure: float, chandelier: float}
    chosen: Literal["zone", "structure", "chandelier"]
    distance_atr: float
    guardrails_hit: List[str]
    reasoning: str

@dataclass
class Target:
    price: float
    r_multiple: float
    size_pct: float
    level_source: str

@dataclass
class ExitPlan:
    targets: List[Target]
    allocation_profile: str
    reasoning: str

@dataclass
class TrailUpdate:
    stage: int  # 1 | 2 | 3 | 4
    new_sl: float
    trigger: str
    timestamp: datetime

@dataclass
class ExitEvent:
    type: Literal["PARTIAL", "FULL"]
    qty: int
    price: float
    reason: str
    timestamp: datetime

@dataclass
class TimeStopPolicy:
    initial_deadline: datetime
    mid_check_deadline: datetime
    hard_cutoff: datetime
    reasoning: str

@dataclass
class HeatCheckResult:
    allow: bool
    total_heat_after: float
    sector_heat_after: float
    max_correlation: float
    effective_heat_after: float
    veto_reason: Optional[str]

@dataclass
class RiskStatus:
    tier: int  # 0 | 1 | 2 | 3 | 4
    size_multiplier: float
    min_tier_allowed: Optional[str]
    max_open_trades: int
    session_pnl_pct: float
    consecutive_losses: int
    halt_until: Optional[datetime]
    reasoning: str

@dataclass
class ApprovedSignal:
    symbol: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    setup_type: str                   # TRAP_FADE | TREND_CONTINUATION | ...
    raw_score: float
    smc_tier: str                     # MONEY | ELITE | STRONG | GOOD | MINOR
    vp_tier: str
    regime: str
    signal_ts: datetime
    metadata: Dict[str, Any]

@dataclass
class TradeDecision:
    action: Literal["EXECUTED", "VETOED", "DEFERRED"]
    order_ref: Optional[str]
    sizing: Optional[SizingDecision]
    sl: Optional[SLDecision]
    exits: Optional[ExitPlan]
    time_stop: Optional[TimeStopPolicy]
    heat_check: HeatCheckResult
    risk_status: RiskStatus
    veto_reason: Optional[str]
    reasoning: str

@dataclass
class OpenPosition:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    entry_ts: datetime
    qty_initial: int
    qty_remaining: int
    current_sl: float
    targets: List[Target]
    trail_stage: int
    r_realized: float
    metadata: Dict[str, Any]

@dataclass
class MarketContext:
    atr_5m: float
    liquidity_tier: str
    regime: str
    level_set: Any
    smc_state: Any
    active_window: str
    stock_adv: float  # average daily value
    prior_session_ohlc: Dict[str, float]
