from dataclasses import dataclass, field
from datetime import datetime
try:
    from typing import Dict, Any, List, Optional
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, List, Optional, Union
    Literal = Any # Fallback if typing_extensions not available

@dataclass
class RegimeDecision:
    regime: Literal["TRENDING_HIGH_VOL", "TRENDING_LOW_VOL", "MEAN_REVERTING", "CHOPPY_UNTRADEABLE"]
    confidence: float                  # 0–1
    allow_trades: bool                 # False only for CHOPPY
    param_overrides: Dict[str, Any]    # Overrides for PriceActionEngine
    feature_snapshot: Dict[str, float] # all 10 raw features
    reasoning: str                     # human-readable explanation
    timestamp: datetime = field(default_factory=datetime.now)
