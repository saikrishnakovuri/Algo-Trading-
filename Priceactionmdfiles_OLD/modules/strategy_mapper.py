"""
Strategy Mapper — given context, returns ordered list 
of strategies to attempt (highest priority first).
Also enforces NO TRADE zones and regime blocks.
"""

from dataclasses import dataclass
from typing import List
from modules.context_detector import MarketContext

@dataclass
class StrategyCandidate:
    name: str
    priority: int          # 1=highest
    min_confidence: float  # min score to take trade
    risk_multiplier: float # 1.0=normal, 0.5=half size
    rationale: str         # why this strategy here

# ══════════════════════════════════════════════════════
# MASTER STRATEGY ROUTING MAP
# ══════════════════════════════════════════════════════
STRATEGY_MAP = {
    "TRENDING_UP": [
        StrategyCandidate("CANDLESTICK", 1, 55, 1.0, "V1 Hero"),
    ],
    "TRENDING_DOWN": [
        StrategyCandidate("VWAP_BOUNCE", 1, 52, 1.0, "V1 Down"),
        StrategyCandidate("CANDLESTICK", 2, 55, 1.0, "V1 Down"),
        StrategyCandidate("MOMENTUM_BREAKOUT", 3, 60, 1.0, "V1 Down"),
    ],
    "RANGING": [
        StrategyCandidate("MEAN_REVERSION", 1, 55, 0.8, "V1 Ranging"),
    ],
    "LOW_VOL": [], # KILLED 20b
    "HIGH_VOL": [
        StrategyCandidate("MEAN_REVERSION", 1, 55, 0.6, "Insurance only"),
    ],
    "BREAKOUT_SETUP": [], # KILLED 20b
    "VOLATILE":  [
        StrategyCandidate("MEAN_REVERSION", 1, 55, 0.6, "Keep insurance"),
    ],
    "CHOPPY":    [
        StrategyCandidate("MEAN_REVERSION", 1, 55, 0.6, "Different mechanic — insurance"),
    ],
}

NO_TRADE_CONDITIONS = [
    lambda ctx: ctx.regime == "VOLATILE",          # true chaos only
    lambda ctx: ctx.vix_state == "EXTREME",
    lambda ctx: ctx.time_zone == "OPENING",        # 9:15-9:45 noise
    lambda ctx: ctx.time_zone == "CLOSING",        # post-14:30
    lambda ctx: ctx.volatility == "EXTREME",
]

# ── Max simultaneous strategies ──────────────────────
MAX_STRATEGIES = {
    "TRENDING_UP":    1,
    "TRENDING_DOWN":  3,
    "RANGING":        1,
    "LOW_VOL":        0,  # REGIME DISABLED
    "HIGH_VOL":       1,
    "BREAKOUT_SETUP": 0,  # REGIME DISABLED
    "VOLATILE":       1,
    "CHOPPY":         1,
}

class StrategyMapper:
    def get_candidates(self, ctx: MarketContext) -> List[StrategyCandidate]:
        """Returns ordered strategy candidates for context."""
        # Check hard NO TRADE conditions
        for condition in NO_TRADE_CONDITIONS:
            if condition(ctx):
                return []

        candidates = STRATEGY_MAP.get(ctx.regime, [])
        max_n = MAX_STRATEGIES.get(ctx.regime, 0)
        return candidates[:max_n]

    def get_risk_multiplier(self, ctx: MarketContext) -> float:
        """Overall risk scaling for current context."""
        if ctx.vix_state == "HIGH":     return 0.5
        if ctx.volatility == "HIGH":    return 0.5
        if ctx.regime == "RANGING":     return 0.8
        if ctx.regime == "BREAKOUT_SETUP": return 1.2
        return 1.0
