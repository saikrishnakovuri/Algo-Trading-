import logging
import json
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


logger = logging.getLogger(__name__)


PENDING_BODY_CLOSE = "PENDING_BODY_CLOSE"
WAITING_RETEST = "WAITING_RETEST"
READY = "READY"
INVALIDATED = "INVALIDATED"
EXPIRED = "EXPIRED"
HIGH_MANIPULATION_RISK = "HIGH_MANIPULATION_RISK"


@dataclass
class NarrativeState:
    active_setups: Dict[str, "MarketSetup"] = field(default_factory=dict)
    history: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class MarketSetup:
    setup_id: str
    symbol: str
    direction: str
    level: float
    source: str
    state: str
    created_bar_idx: int
    updated_bar_idx: int
    created_at: Any = None
    body_close_bar_idx: Optional[int] = None
    retest_bar_idx: Optional[int] = None
    invalidation_level: Optional[float] = None
    expiry_bars: int = 12
    retest_expiry_bars: int = 12
    confidence: float = 55.0
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state in (PENDING_BODY_CLOSE, WAITING_RETEST, READY)


class MarketMemoryEngine:
    """
    Central market narrative state manager.

    This engine is intentionally additive. It does not replace individual
    strategy engines. It remembers raw structure events across refreshes and
    turns a multi-candle story into a signal only after body close and retest.
    """

    def __init__(
        self,
        max_pending_bars: int = 8,
        max_retest_bars: int = 12,
        max_setups_per_symbol: int = 3,
        double_sweep_window_bars: int = 10,
        manipulation_cooldown_bars: int = 10,
        manipulation_veto_weight: float = 0.95,
    ):
        self.max_pending_bars = max_pending_bars
        self.max_retest_bars = max_retest_bars
        self.max_setups_per_symbol = max_setups_per_symbol
        self.double_sweep_window_bars = double_sweep_window_bars
        self.manipulation_cooldown_bars = manipulation_cooldown_bars
        self.manipulation_veto_weight = manipulation_veto_weight
        self.setups: Dict[str, List[MarketSetup]] = {}
        self.completed: List[MarketSetup] = []
        self.history: Dict[str, Dict[str, Any]] = {}
        self.narrative: Dict[str, NarrativeState] = {}

    def reset(self, symbol: Optional[str] = None) -> None:
        if symbol is None:
            self.setups = {}
            self.completed = []
            self.history = {}
            self.narrative = {}
            return
        self.completed.extend(self.setups.get(symbol, []))
        self.setups[symbol] = []
        self.history[symbol] = {}
        self.narrative[symbol] = NarrativeState()

    def update(
        self,
        symbol: str,
        df: pd.DataFrame,
        events: Optional[Iterable[Dict[str, Any]]] = None,
        context: Any = None,
    ) -> List[MarketSetup]:
        if df is None or df.empty:
            return []

        frame = self._normalise_frame(df)
        current_idx = len(frame) - 1
        current = frame.iloc[-1]

        if events:
            self.ingest_events(symbol, events, current_idx=current_idx, timestamp=frame.index[-1])

        for setup in list(self.setups.get(symbol, [])):
            self._advance_setup(setup, current, current_idx, context=context)

        self._prune(symbol)
        return self.active_setups(symbol)

    def ingest_events(
        self,
        symbol: str,
        events: Iterable[Dict[str, Any]],
        current_idx: Optional[int] = None,
        timestamp: Any = None,
    ) -> List[MarketSetup]:
        created = []
        for event in events:
            if self._handle_narrative_event(symbol, event, current_idx, timestamp):
                continue
            setup = self._setup_from_event(symbol, event, current_idx, timestamp)
            if setup is None:
                continue
            if self._already_tracking(symbol, setup):
                continue
            self.setups.setdefault(symbol, []).append(setup)
            created.append(setup)

        if created:
            logger.debug("[MEMORY] %s created %d setup(s)", symbol, len(created))
        self._prune(symbol)
        return created

    def is_manipulation_risk(self, symbol: Optional[str] = None, current_idx: Optional[int] = None) -> bool:
        symbols = [symbol] if symbol is not None else list(self.history.keys())
        for sym in symbols:
            hist = self.history.get(sym, {})
            risk = hist.get("manipulation_risk")
            if not risk:
                continue
            expires_at = risk.get("expires_at")
            if current_idx is None or expires_at is None or current_idx <= expires_at:
                return True
            hist["manipulation_risk"] = None
        return False

    def manipulation_reason(self, symbol: str) -> Optional[str]:
        risk = self.history.get(symbol, {}).get("manipulation_risk")
        if not risk:
            return None
        return risk.get("reason", HIGH_MANIPULATION_RISK)

    def manipulation_weight(self, symbol: str) -> float:
        risk = self.history.get(symbol, {}).get("manipulation_risk")
        if not risk:
            return 0.0
        return float(risk.get("weight", 0.0))

    def should_veto_for_manipulation(self, symbol: str, current_idx: Optional[int] = None) -> bool:
        if not self.is_manipulation_risk(symbol, current_idx=current_idx):
            return False
        return self.manipulation_weight(symbol) >= self.manipulation_veto_weight

    def narrative_state(self, symbol: str) -> NarrativeState:
        active = {setup.setup_id: setup for setup in self.active_setups(symbol)}
        hist = self.history.setdefault(symbol, {})
        state = NarrativeState(
            active_setups=active,
            history=hist,
            weights=dict(hist.get("weights", {})),
        )
        self.narrative[symbol] = state
        return state

    def save_state(self, filepath: str) -> None:
        """Persist active/completed narrative memory for crash recovery."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "setups": {
                symbol: [self._json_safe(asdict(setup)) for setup in setups]
                for symbol, setups in self.setups.items()
            },
            "completed": [self._json_safe(asdict(setup)) for setup in self.completed],
            "history": self._json_safe(self.history),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_state(self, filepath: str) -> bool:
        """Load persisted narrative memory. Returns False when no usable state exists."""
        path = Path(filepath)
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load market memory state from %s: %s", filepath, exc)
            return False

        try:
            self.setups = {
                symbol: [self._setup_from_payload(item) for item in setups]
                for symbol, setups in payload.get("setups", {}).items()
            }
            self.completed = [
                self._setup_from_payload(item)
                for item in payload.get("completed", [])
            ]
            self.history = self._restore_json_values(payload.get("history", {}))
            self.narrative = {}
            return True
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid market memory state in %s: %s", filepath, exc)
            return False

    def ingest_smc_state(
        self,
        symbol: str,
        smc_state: Any,
        current_idx: Optional[int] = None,
        timestamp: Any = None,
    ) -> List[MarketSetup]:
        return self.ingest_events(
            symbol,
            self.events_from_smc_state(smc_state),
            current_idx=current_idx,
            timestamp=timestamp,
        )

    def has_active_setups(self, symbol: Optional[str] = None) -> bool:
        if symbol is not None:
            return any(s.is_active() for s in self.setups.get(symbol, []))
        return any(s.is_active() for setups in self.setups.values() for s in setups)

    def active_setups(self, symbol: Optional[str] = None) -> List[MarketSetup]:
        if symbol is not None:
            return [s for s in self.setups.get(symbol, []) if s.is_active()]
        return [s for setups in self.setups.values() for s in setups if s.is_active()]

    def ready_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        ready = [s for s in self.setups.get(symbol, []) if s.state == READY]
        if not ready:
            return None

        setup = max(ready, key=lambda s: (s.confidence, s.updated_bar_idx))
        close = float(self._normalise_frame(df).iloc[-1]["close"])
        direction = "CE" if setup.direction == "BULL" else "PE"
        risk = abs(close - setup.invalidation_level) if setup.invalidation_level else close * 0.003
        if risk <= 0:
            risk = close * 0.003

        sl = setup.invalidation_level
        if sl is None:
            sl = close - risk if direction == "CE" else close + risk
        tp = close + risk * 2.0 if direction == "CE" else close - risk * 2.0

        setup.state = "CONSUMED"
        self.completed.append(setup)
        return {
            "signal": "BUY" if direction == "CE" else "SELL",
            "direction": direction,
            "options_direction": direction,
            "entry_price": close,
            "spot_price": close,
            "sl": round(float(sl), 2),
            "tp": round(float(tp), 2),
            "confidence": setup.confidence,
            "setup_type": "MARKET_MEMORY_%s" % setup.source,
            "memory_setup_id": setup.setup_id,
            "memory_state": setup.state,
            "reasons": list(setup.reasons) + ["market_memory_retest_confirmed"],
        }

    def events_from_smc_state(self, smc_state: Any) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        if not smc_state:
            return events

        structure = getattr(smc_state, "structure", None)
        if structure:
            for key, event_type in (("last_BOS", "body_close"), ("last_CHoCH", "choch")):
                raw = getattr(structure, key, None)
                if raw:
                    events.append(
                        {
                            "type": event_type,
                            "direction": raw.get("direction"),
                            "level": raw.get("broken_level", raw.get("price")),
                            "price": raw.get("price"),
                            "bar_idx": raw.get("bar_idx"),
                            "source": "SMC_%s" % key,
                        }
                    )
            reclaim = getattr(structure, "last_reclaim", None)
            if reclaim:
                events.append(
                    {
                        "type": "structure_reclaim",
                        "direction": reclaim.get("direction"),
                        "level": reclaim.get("level"),
                        "bar_idx": reclaim.get("bar_idx"),
                        "source": "SMC_RECLAIM",
                    }
                )

        for sweep in getattr(smc_state, "active_sweeps", []) or []:
            if getattr(sweep, "status", "ACTIVE") != "ACTIVE":
                continue
            pool_type = str(getattr(sweep, "pool_type", ""))
            direction = "BULL" if "L" in pool_type else "BEAR"
            events.append(
                {
                    "type": "wick_break",
                    "direction": direction,
                    "level": getattr(sweep, "pool_level", None),
                    "extreme": getattr(sweep, "sweep_price", None),
                    "bar_idx": getattr(sweep, "sweep_candle_idx", None),
                    "source": "SMC_SWEEP_%s" % pool_type,
                    "confidence": 58 + max(0, 3 - int(getattr(sweep, "tier", 3))) * 6,
                }
            )

        return events

    def _setup_from_event(
        self,
        symbol: str,
        event: Dict[str, Any],
        current_idx: Optional[int],
        timestamp: Any,
    ) -> Optional[MarketSetup]:
        level = event.get("level")
        if level is None:
            return None

        direction = self._normalise_direction(event.get("direction"))
        if direction not in ("BULL", "BEAR"):
            return None

        event_type = str(event.get("type", "")).lower()
        bar_idx = event.get("bar_idx")
        if bar_idx is None:
            bar_idx = current_idx if current_idx is not None else 0
        bar_idx = int(bar_idx)

        state = WAITING_RETEST if event_type in ("body_close", "bos") else PENDING_BODY_CLOSE
        source = str(event.get("source") or event_type or "STRUCTURE")
        setup_id = "%s:%s:%s:%.4f:%s" % (symbol, source, direction, float(level), bar_idx)
        invalidation_level = event.get("invalidation_level")
        if invalidation_level is None:
            invalidation_level = event.get("extreme")

        return MarketSetup(
            setup_id=setup_id,
            symbol=symbol,
            direction=direction,
            level=float(level),
            source=source,
            state=state,
            created_bar_idx=bar_idx,
            updated_bar_idx=bar_idx,
            created_at=timestamp if timestamp is not None else datetime.now(),
            body_close_bar_idx=bar_idx if state == WAITING_RETEST else None,
            invalidation_level=float(invalidation_level) if invalidation_level is not None else None,
            expiry_bars=int(event.get("expiry_bars", self.max_pending_bars)),
            retest_expiry_bars=int(event.get("retest_expiry_bars", self.max_retest_bars)),
            confidence=float(event.get("confidence", 60 if state == WAITING_RETEST else 52)),
            reasons=[event_type or "structure_event"],
            metadata={**dict(event), "weight": self._event_weight(event)},
        )

    def _advance_setup(
        self,
        setup: MarketSetup,
        candle: pd.Series,
        current_idx: int,
        context: Any = None,
    ) -> None:
        if setup.state == PENDING_BODY_CLOSE:
            if current_idx - setup.created_bar_idx > setup.expiry_bars:
                self._expire(setup, current_idx, "pending_body_close_timeout")
                return
            if self._opposite_structure_broken(setup, candle):
                self._invalidate(setup, current_idx, "opposite_structure_broken")
                return
            if self._body_closed_beyond_level(setup, candle):
                setup.state = WAITING_RETEST
                setup.body_close_bar_idx = current_idx
                setup.updated_bar_idx = current_idx
                setup.confidence += 8
                setup.reasons.append("body_close_confirmed")
                logger.debug("[MEMORY] %s body close confirmed at %.2f", setup.symbol, setup.level)
            return

        if setup.state == WAITING_RETEST:
            base_idx = setup.body_close_bar_idx if setup.body_close_bar_idx is not None else setup.created_bar_idx
            if current_idx - base_idx > setup.retest_expiry_bars:
                self._expire(setup, current_idx, "retest_timeout")
                return
            if self._structure_reclaimed(setup, candle):
                self._invalidate(setup, current_idx, "structure_reclaimed")
                self._remember_failed_retest(setup, current_idx)
                return
            if self._opposite_structure_broken(setup, candle):
                self._invalidate(setup, current_idx, "opposite_structure_broken")
                return
            if self._retested_level(setup, candle):
                setup.state = READY
                setup.retest_bar_idx = current_idx
                setup.updated_bar_idx = current_idx
                setup.confidence = min(95.0, setup.confidence + 12)
                setup.reasons.append("retest_confirmed")
                logger.debug("[MEMORY] %s retest confirmed at %.2f", setup.symbol, setup.level)

    def _body_closed_beyond_level(self, setup: MarketSetup, candle: pd.Series) -> bool:
        open_price = float(candle["open"])
        close = float(candle["close"])
        body_high = max(open_price, close)
        body_low = min(open_price, close)
        if setup.direction == "BULL":
            return body_high > setup.level and close > setup.level
        return body_low < setup.level and close < setup.level

    def _retested_level(self, setup: MarketSetup, candle: pd.Series) -> bool:
        low = float(candle["low"])
        high = float(candle["high"])
        close = float(candle["close"])
        if setup.direction == "BULL":
            return low <= setup.level <= high and close >= setup.level
        return low <= setup.level <= high and close <= setup.level

    def _structure_reclaimed(self, setup: MarketSetup, candle: pd.Series) -> bool:
        close = float(candle["close"])
        if setup.direction == "BULL":
            return close < setup.level
        return close > setup.level

    def _opposite_structure_broken(self, setup: MarketSetup, candle: pd.Series) -> bool:
        if setup.invalidation_level is None:
            return False
        close = float(candle["close"])
        if setup.direction == "BULL":
            return close < setup.invalidation_level
        return close > setup.invalidation_level

    def _handle_narrative_event(
        self,
        symbol: str,
        event: Dict[str, Any],
        current_idx: Optional[int],
        timestamp: Any,
    ) -> bool:
        event_type = str(event.get("type", "")).lower()
        if event_type in ("wick_break", "sweep", "liquidity_sweep"):
            self._record_sweep(symbol, event, current_idx, timestamp)
            return False
        if event_type in ("body_close", "bos", "external_bos", "ebos"):
            self._resolve_manipulation_on_clean_bos(symbol, event, current_idx)
            return False
        if event_type in ("structure_reclaim", "reclaim", "retest_failure"):
            self._invalidate_reclaimed_setups(symbol, event, current_idx)
            return True
        self._record_weight(symbol, event_type or "unknown", self._event_weight(event))
        return False

    def _record_sweep(
        self,
        symbol: str,
        event: Dict[str, Any],
        current_idx: Optional[int],
        timestamp: Any,
    ) -> None:
        direction = self._normalise_direction(event.get("direction"))
        if direction not in ("BULL", "BEAR"):
            return

        bar_idx = event.get("bar_idx")
        if bar_idx is None:
            bar_idx = current_idx if current_idx is not None else 0
        bar_idx = int(bar_idx)
        hist = self.history.setdefault(symbol, {})
        sweeps = hist.setdefault("sweep_sequence", [])
        sweep = {
            "direction": direction,
            "time": timestamp,
            "level": event.get("level"),
            "bar_idx": bar_idx,
            "source": event.get("source"),
            "weight": self._event_weight(event),
        }
        sweeps.append(sweep)
        self._record_weight(symbol, "sweep", sweep["weight"])
        hist["last_sweep"] = sweep
        hist["sweep_sequence"] = [
            item for item in sweeps
            if bar_idx - int(item.get("bar_idx", bar_idx)) <= self.double_sweep_window_bars
        ]
        hist["sweep_count_window"] = len(hist["sweep_sequence"])

        for prior in hist["sweep_sequence"][:-1]:
            if prior.get("direction") != direction:
                weight = self._double_sweep_weight(prior, sweep)
                hist["manipulation_risk"] = {
                    "reason": HIGH_MANIPULATION_RISK,
                    "event": "double_sweep",
                    "weight": weight,
                    "first_sweep": prior,
                    "second_sweep": sweep,
                    "bar_idx": bar_idx,
                    "expires_at": bar_idx + self.manipulation_cooldown_bars,
                }
                self._record_weight(symbol, "double_sweep", weight)
                logger.debug("[MEMORY] %s double sweep manipulation risk", symbol)
                break

    def _resolve_manipulation_on_clean_bos(
        self,
        symbol: str,
        event: Dict[str, Any],
        current_idx: Optional[int],
    ) -> None:
        hist = self.history.setdefault(symbol, {})
        risk = hist.get("manipulation_risk")
        if not risk:
            return
        direction = self._normalise_direction(event.get("direction"))
        if direction in ("BULL", "BEAR"):
            risk["resolved_by"] = {
                "direction": direction,
                "level": event.get("level"),
                "bar_idx": current_idx if current_idx is not None else event.get("bar_idx"),
                "weight": self._event_weight(event),
            }
            hist["manipulation_risk"] = None

    def _invalidate_reclaimed_setups(
        self,
        symbol: str,
        event: Dict[str, Any],
        current_idx: Optional[int],
    ) -> None:
        direction = self._normalise_direction(event.get("direction"))
        level = event.get("level")
        if direction not in ("BULL", "BEAR") or level is None:
            return
        level = float(level)
        idx = int(current_idx if current_idx is not None else event.get("bar_idx", 0))
        for setup in self.setups.get(symbol, []):
            if setup.direction != direction or not setup.is_active():
                continue
            if abs(setup.level - level) <= max(0.05, level * 0.0001):
                self._invalidate(setup, idx, "structure_reclaimed")
                self._remember_failed_retest(setup, idx)

    def _remember_failed_retest(self, setup: MarketSetup, current_idx: int) -> None:
        hist = self.history.setdefault(setup.symbol, {})
        hist["last_failed_retest"] = {
            "time": setup.created_at,
            "level": setup.level,
            "direction": setup.direction,
            "bar_idx": current_idx,
            "setup_id": setup.setup_id,
            "weight": max(float(setup.metadata.get("weight", 0.0)), 0.86),
        }
        self._record_weight(setup.symbol, "failed_retest", hist["last_failed_retest"]["weight"])

    def _expire(self, setup: MarketSetup, current_idx: int, reason: str) -> None:
        setup.state = EXPIRED
        setup.updated_bar_idx = current_idx
        setup.reasons.append(reason)

    def _invalidate(self, setup: MarketSetup, current_idx: int, reason: str) -> None:
        setup.state = INVALIDATED
        setup.updated_bar_idx = current_idx
        setup.reasons.append(reason)

    def _prune(self, symbol: str) -> None:
        setups = self.setups.get(symbol, [])
        still_tracked = []
        for setup in setups:
            if setup.state in (INVALIDATED, EXPIRED, "CONSUMED"):
                self.completed.append(setup)
            else:
                still_tracked.append(setup)
        self.setups[symbol] = sorted(
            still_tracked,
            key=lambda s: (s.updated_bar_idx, s.confidence),
            reverse=True,
        )[: self.max_setups_per_symbol]

    def _already_tracking(self, symbol: str, setup: MarketSetup) -> bool:
        for existing in self.setups.get(symbol, []):
            same_direction = existing.direction == setup.direction
            same_level = abs(existing.level - setup.level) <= max(0.05, setup.level * 0.0001)
            same_source = existing.source == setup.source
            if same_direction and same_level and same_source and existing.is_active():
                return True
        return False

    def _record_weight(self, symbol: str, event_name: str, weight: float) -> None:
        hist = self.history.setdefault(symbol, {})
        weights = hist.setdefault("weights", {})
        weights[event_name] = max(float(weights.get(event_name, 0.0)), float(weight))

    def _event_weight(self, event: Dict[str, Any]) -> float:
        if "weight" in event:
            return self._clamp_weight(event.get("weight"))

        event_type = str(event.get("type", "")).lower()
        source = str(event.get("source", "")).lower()

        if event_type in ("double_sweep",):
            return 0.92
        if event_type in ("structure_reclaim", "reclaim", "retest_failure"):
            return 0.88
        if event_type in ("external_bos", "ebos"):
            return 0.76
        if event_type in ("body_close", "bos"):
            return 0.68 if "last_bos" in source or "external" in source else 0.58
        if event_type in ("choch",):
            return 0.72
        if event_type in ("wick_break", "sweep", "liquidity_sweep"):
            confidence = event.get("confidence")
            if confidence is not None:
                return self._clamp_weight(float(confidence) / 100.0)
            return 0.64
        if event_type in ("minor_internal_bos", "internal_bos", "ibos"):
            return 0.41

        return 0.50

    def _double_sweep_weight(self, first: Dict[str, Any], second: Dict[str, Any]) -> float:
        first_weight = float(first.get("weight", 0.64))
        second_weight = float(second.get("weight", 0.64))
        distance = abs(int(second.get("bar_idx", 0)) - int(first.get("bar_idx", 0)))
        proximity_bonus = max(0.0, (self.double_sweep_window_bars - distance) / max(self.double_sweep_window_bars, 1)) * 0.10
        base = max(first_weight, second_weight)
        if first_weight >= 0.60 and second_weight >= 0.60:
            base = max(base, 0.87)
        return self._clamp_weight(base + proximity_bonus)

    def _clamp_weight(self, weight: Any) -> float:
        try:
            value = float(weight)
        except (TypeError, ValueError):
            value = 0.50
        return max(0.0, min(1.0, value))

    def _normalise_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        frame = df.copy()
        frame.columns = [str(c).lower() for c in frame.columns]
        return frame

    def _normalise_direction(self, direction: Any) -> Optional[str]:
        value = str(direction or "").upper()
        if value in ("BULL", "BULLISH", "LONG", "BUY", "CE", "UP"):
            return "BULL"
        if value in ("BEAR", "BEARISH", "SHORT", "SELL", "PE", "DOWN"):
            return "BEAR"
        return None

    def _setup_from_payload(self, payload: Dict[str, Any]) -> MarketSetup:
        restored = self._restore_json_values(payload)
        return MarketSetup(**restored)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except TypeError:
                pass
        return value

    def _restore_json_values(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._restore_json_values(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._restore_json_values(item) for item in value]
        if isinstance(value, str):
            return self._maybe_parse_datetime(value)
        return value

    def _maybe_parse_datetime(self, value: str) -> Any:
        if "T" not in value and " " not in value:
            return value
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
