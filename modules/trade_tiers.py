from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class TradeTierDecision:
    tier: str
    label: str
    risk_multiplier: float
    min_confidence: float
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "label": self.label,
            "risk_multiplier": self.risk_multiplier,
            "min_confidence": self.min_confidence,
            "reason": self.reason,
        }


class TradeTierResolver:
    """
    Assigns participation tiers after existing strategy scoring.

    This layer does not remove safety filters. It classifies surviving or
    near-surviving signals into size/conviction buckets.
    """

    STRICT_MIN = {
        "A": 70.0,
        "B": 60.0,
        "C": 54.0,
    }

    PARTICIPATION_MIN = {
        "A": 68.0,
        "B": 56.0,
        "C": 50.0,
    }

    def classify(
        self,
        signal: Dict[str, Any],
        ctx: Any = None,
        mode: str = "NORMAL",
        hierarchy_decision: Optional[Dict[str, Any]] = None,
        manipulation_weight: float = 0.0,
    ) -> TradeTierDecision:
        confidence = float(signal.get("confidence") or 0.0)
        mode_key = str(mode or "NORMAL").upper()
        mins = self.PARTICIPATION_MIN if mode_key in ("BALANCED", "PARTICIPATION") else self.STRICT_MIN

        hierarchy_delta = 0.0
        hierarchy_warnings = []
        if hierarchy_decision:
            hierarchy_delta = float(hierarchy_decision.get("confidence_delta") or 0.0)
            hierarchy_warnings = hierarchy_decision.get("warnings") or []

        strategy = str(signal.get("strategy") or "").upper()
        raw = signal.get("raw_signal") if isinstance(signal.get("raw_signal"), dict) else {}
        setup_type = str(raw.get("setup_type") or raw.get("state") or raw.get("event") or "").lower()

        if confidence >= mins["A"] and manipulation_weight < 0.70 and hierarchy_delta >= -8:
            return TradeTierDecision(
                tier="A",
                label="HIGH_CONVICTION",
                risk_multiplier=1.0,
                min_confidence=mins["A"],
                reason="strict filters passed",
            )

        if confidence >= mins["B"] and manipulation_weight < 0.95:
            risk = 0.55
            reason = "moderate conviction"
            if hierarchy_delta < -8:
                risk = 0.70
                reason = "countertrend or weak HTF alignment; reduced size"
            if "internal" in setup_type or "ibos" in setup_type:
                reason = "internal structure accepted as Tier B"
            return TradeTierDecision(
                tier="B",
                label="MODERATE_CONVICTION",
                risk_multiplier=risk,
                min_confidence=mins["B"],
                reason=reason,
            )

        is_low_vol = False
        if ctx is not None:
            regime = str(getattr(ctx, "regime", "")).upper()
            volatility = str(getattr(ctx, "volatility", "")).upper()
            is_low_vol = regime in ("COMPRESSION", "RANGING", "CHOPPY") or volatility in ("LOW", "COMPRESSED")

        scalp_candidate = (
            confidence >= mins["C"]
            and manipulation_weight < 0.70
            and (is_low_vol or strategy in ("CANDLESTICK", "MOMENTUM_BREAKOUT", "MARKET_MEMORY"))
            and not hierarchy_warnings
        )
        if scalp_candidate:
            return TradeTierDecision(
                tier="C",
                label="SCALP_OPPORTUNISTIC",
                risk_multiplier=0.25,
                min_confidence=mins["C"],
                reason="participation scalp with small size",
            )

        return TradeTierDecision(
            tier="REJECT",
            label="NO_TIER",
            risk_multiplier=0.0,
            min_confidence=mins["C"],
            reason="below adaptive tier requirements",
        )

    def threshold_for_mode(self, strict_threshold: float, mode: str) -> float:
        mode_key = str(mode or "NORMAL").upper()
        if mode_key == "AGGRESSIVE":
            return min(strict_threshold, self.PARTICIPATION_MIN["B"])
        if mode_key == "BALANCED":
            return min(strict_threshold, self.PARTICIPATION_MIN["B"])
        if mode_key == "PARTICIPATION":
            return min(strict_threshold, self.PARTICIPATION_MIN["C"])
        return strict_threshold
