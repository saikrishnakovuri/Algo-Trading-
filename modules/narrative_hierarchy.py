from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


BULL = "BULL"
BEAR = "BEAR"
NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class TimeframeNarrative:
    timeframe: str
    bias: str
    confidence: float
    state: str
    weight: float


@dataclass(frozen=True)
class HierarchyDecision:
    dominant_bias: str
    trade_allowed: bool
    adjusted_confidence: Optional[float]
    confidence_delta: float
    score: float
    reason: str
    warnings: List[str] = field(default_factory=list)
    contributions: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dominant_bias": self.dominant_bias,
            "trade_allowed": self.trade_allowed,
            "adjusted_confidence": self.adjusted_confidence,
            "confidence_delta": self.confidence_delta,
            "score": self.score,
            "reason": self.reason,
            "warnings": list(self.warnings),
            "contributions": dict(self.contributions),
        }


class NarrativeHierarchyResolver:
    """
    Resolves which timeframe narrative should dominate.

    This class does not detect BOS, sweeps, CHOCH, or retests. It only compares
    already-detected narratives and returns a bias/confidence decision.
    """

    TIMEFRAME_IMPORTANCE = {
        "1m": 0.30,
        "3m": 0.40,
        "5m": 0.50,
        "15m": 0.90,
        "30m": 0.95,
        "1h": 1.00,
        "60m": 1.00,
        "1d": 1.20,
        "d": 1.20,
    }

    STATE_IMPORTANCE = {
        "internal_bos": 0.70,
        "minor_internal_bos": 0.41,
        "ibos": 0.70,
        "bos": 0.78,
        "external_bos": 1.00,
        "ebos": 1.00,
        "choch": 0.86,
        "retest_confirmation": 0.76,
        "bullish_retest": 0.76,
        "bearish_retest": 0.76,
        "liquidity_sweep": 0.62,
        "sweep": 0.62,
        "distribution": 0.95,
        "accumulation": 0.85,
        "sideways": 0.25,
        "compression": 0.25,
        "double_sweep": -1.20,
        "high_manipulation_risk": -1.20,
        "reclaimed_structure": -1.00,
        "structure_reclaim": -1.00,
        "failed_retest": -1.00,
    }

    def __init__(
        self,
        conflict_veto_threshold: float = 0.70,
        trap_warning_threshold: float = 0.60,
        alignment_boost: float = 8.0,
        max_confidence_boost: float = 12.0,
        max_confidence_penalty: float = -35.0,
    ):
        self.conflict_veto_threshold = conflict_veto_threshold
        self.trap_warning_threshold = trap_warning_threshold
        self.alignment_boost = alignment_boost
        self.max_confidence_boost = max_confidence_boost
        self.max_confidence_penalty = max_confidence_penalty

    def resolve(
        self,
        narratives: Dict[str, Dict[str, Any]],
        trade_direction: Optional[str] = None,
        base_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        parsed = self._parse_narratives(narratives)
        if not parsed:
            return HierarchyDecision(
                dominant_bias=NEUTRAL,
                trade_allowed=True,
                adjusted_confidence=base_confidence,
                confidence_delta=0.0,
                score=0.0,
                reason="no timeframe narratives supplied",
            ).as_dict()

        contributions = self._score_contributions(parsed)
        total_score = sum(contributions.values())
        dominant_bias = self._dominant_bias(total_score)
        trade_bias = self._normalise_bias(trade_direction)
        htf_conflict = self._strongest_htf_conflict(parsed, trade_bias)
        manipulation_penalty = self._manipulation_penalty(parsed)
        alignment = self._all_directional_timeframes_align(parsed)
        warnings = []

        confidence_delta = 0.0
        trade_allowed = True
        reason = self._dominant_reason(parsed, dominant_bias)

        if alignment:
            confidence_delta += self.alignment_boost
            reason = "timeframe alignment supports %s continuation" % dominant_bias

        if trade_bias in (BULL, BEAR) and htf_conflict:
            conflict_tf, conflict = htf_conflict
            penalty = min(35.0, abs(conflict.weight) * 35.0)
            confidence_delta -= penalty
            reason = "%s %s dominates lower timeframe %s setup" % (
                conflict_tf,
                self._describe_state(conflict),
                trade_bias.lower(),
            )
            if abs(conflict.weight) >= self.conflict_veto_threshold:
                trade_allowed = False

        if manipulation_penalty <= -self.trap_warning_threshold:
            warnings.append("possible short trap warning" if trade_bias == BULL else "manipulation risk")
            confidence_delta += max(self.max_confidence_penalty, manipulation_penalty * 20.0)
            if manipulation_penalty <= -0.90:
                trade_allowed = False
                reason = "high-weight manipulation narrative overrides trade setup"

        confidence_delta = max(self.max_confidence_penalty, min(self.max_confidence_boost, confidence_delta))
        adjusted = None if base_confidence is None else max(0.0, min(100.0, float(base_confidence) + confidence_delta))

        return HierarchyDecision(
            dominant_bias=dominant_bias,
            trade_allowed=trade_allowed,
            adjusted_confidence=adjusted,
            confidence_delta=confidence_delta,
            score=total_score + manipulation_penalty,
            reason=reason,
            warnings=warnings,
            contributions=contributions,
        ).as_dict()

    def _parse_narratives(self, narratives: Dict[str, Dict[str, Any]]) -> List[TimeframeNarrative]:
        parsed = []
        for timeframe, raw in (narratives or {}).items():
            if not isinstance(raw, dict):
                continue
            bias = self._normalise_bias(raw.get("bias") or raw.get("direction"))
            state = str(raw.get("state") or raw.get("event") or "").lower()
            confidence = self._normalise_confidence(raw.get("confidence", 1.0))
            weight = raw.get("weight")
            if weight is None:
                weight = self._default_weight(str(timeframe), state)
            parsed.append(
                TimeframeNarrative(
                    timeframe=str(timeframe),
                    bias=bias,
                    confidence=confidence,
                    state=state,
                    weight=float(weight),
                )
            )
        return parsed

    def _score_contributions(self, narratives: List[TimeframeNarrative]) -> Dict[str, float]:
        contributions = {}
        for item in narratives:
            if item.weight < 0:
                contributions[item.timeframe] = item.weight * item.confidence
                continue
            sign = 1.0 if item.bias == BULL else -1.0 if item.bias == BEAR else 0.0
            contributions[item.timeframe] = sign * item.weight * item.confidence
        return contributions

    def _default_weight(self, timeframe: str, state: str) -> float:
        tf_weight = self.TIMEFRAME_IMPORTANCE.get(timeframe.lower(), 0.50)
        state_weight = self.STATE_IMPORTANCE.get(state.lower(), 0.65)
        if state_weight < 0:
            return state_weight
        return tf_weight * state_weight

    def _strongest_htf_conflict(
        self,
        narratives: List[TimeframeNarrative],
        trade_bias: str,
    ) -> Optional[Tuple[str, TimeframeNarrative]]:
        if trade_bias not in (BULL, BEAR):
            return None
        opposing = [n for n in narratives if n.bias in (BULL, BEAR) and n.bias != trade_bias]
        if not opposing:
            return None
        strongest = max(opposing, key=lambda n: abs(n.weight) * n.confidence)
        if abs(strongest.weight) * strongest.confidence < 0.25:
            return None
        return strongest.timeframe, strongest

    def _manipulation_penalty(self, narratives: List[TimeframeNarrative]) -> float:
        penalty = 0.0
        for item in narratives:
            if item.weight < 0:
                penalty += item.weight * item.confidence
        return penalty

    def _all_directional_timeframes_align(self, narratives: List[TimeframeNarrative]) -> bool:
        directional = [n.bias for n in narratives if n.bias in (BULL, BEAR) and n.weight > 0]
        return len(directional) >= 2 and len(set(directional)) == 1

    def _dominant_bias(self, total_score: float) -> str:
        if total_score > 0.05:
            return BULL
        if total_score < -0.05:
            return BEAR
        return NEUTRAL

    def _dominant_reason(self, narratives: List[TimeframeNarrative], dominant_bias: str) -> str:
        if dominant_bias == NEUTRAL:
            return "timeframe narratives are balanced"
        aligned = [n for n in narratives if n.bias == dominant_bias]
        strongest = max(aligned, key=lambda n: abs(n.weight) * n.confidence)
        return "%s %s is the dominant narrative" % (
            strongest.timeframe,
            self._describe_state(strongest),
        )

    def _describe_state(self, item: TimeframeNarrative) -> str:
        state = item.state.replace("_", " ")
        return "%s %s" % (item.bias.lower(), state)

    def _normalise_bias(self, value: Any) -> str:
        text = str(value or "").upper()
        if text in ("BULL", "BULLISH", "LONG", "BUY", "CE", "UP"):
            return BULL
        if text in ("BEAR", "BEARISH", "SHORT", "SELL", "PE", "DOWN"):
            return BEAR
        return NEUTRAL

    def _normalise_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 1.0
        if confidence > 1.0:
            confidence = confidence / 100.0
        return max(0.0, min(1.0, confidence))
