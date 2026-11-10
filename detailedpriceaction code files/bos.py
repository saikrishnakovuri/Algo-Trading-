"""
Break of Structure (BOS) price-action detector.

This module converts the BOS trading notes into executable Python logic:
- Find swing highs and swing lows.
- Detect bullish and bearish breaks of structure.
- Classify breaks as internal BOS, external BOS, or liquidity BOS.
- Reject wick-only breaks when body-close confirmation is required.
- Confirm momentum/displacement before marking a BOS as valid.
- Separate valid BOS, weak BOS, fake BOS, liquidity grabs, and CHOCH.
- Generate baseline, messy, fake-break, and edge-case test scenarios.
- Build basic trade levels after a confirmed break and retest.

Input candles can be dictionaries with keys:
    time, open, high, low, close, volume

Only high, low, and close are required for structural detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Optional, Sequence


class BOSDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class BOSType(str, Enum):
    INTERNAL = "internal_bos"
    EXTERNAL = "external_bos"
    LIQUIDITY = "liquidity_bos"


class StructureSignal(str, Enum):
    BOS = "bos"
    CHOCH = "choch"
    WICK_BREAK = "wick_break"
    FAKE_BOS = "fake_bos"
    LIQUIDITY_GRAB = "liquidity_grab"


class ValidationStatus(str, Enum):
    VALID = "valid"
    WEAK = "weak"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Candle:
    time: object
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class SwingPoint:
    index: int
    time: object
    price: float
    kind: str  # "high" or "low"


@dataclass(frozen=True)
class BOSEvent:
    index: int
    time: object
    direction: BOSDirection
    bos_type: BOSType
    broken_swing: SwingPoint
    break_price: float
    close_price: float
    signal: StructureSignal
    validation_status: ValidationStatus
    body_close_confirmed: bool
    displacement_confirmed: bool
    volume_confirmed: bool
    retest_confirmed: bool
    reversal_confirmed: bool
    timeframe_conflict: bool
    rejection_reason: Optional[str]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward: Optional[float]


@dataclass(frozen=True)
class TestScenario:
    name: str
    category: str
    expected_signal: StructureSignal
    expected_status: ValidationStatus
    candles: list[Candle]


def normalize_candles(candles: Iterable[Candle | Mapping[str, object]]) -> list[Candle]:
    """Convert dictionaries or Candle instances into Candle objects."""
    normalized: list[Candle] = []

    for i, candle in enumerate(candles):
        if isinstance(candle, Candle):
            normalized.append(candle)
            continue

        normalized.append(
            Candle(
                time=candle.get("time", i),
                open=float(candle.get("open", candle.get("close", 0.0))),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle.get("volume", 0.0)),
            )
        )

    return normalized


def find_swing_points(candles: Sequence[Candle], lookback: int = 2) -> list[SwingPoint]:
    """
    Identify local swing highs and lows.

    A swing high is higher than the highs around it. A swing low is lower than
    the lows around it. Increasing lookback produces fewer, stronger swings.
    """
    if lookback < 1:
        raise ValueError("lookback must be at least 1")

    swings: list[SwingPoint] = []

    for index in range(lookback, len(candles) - lookback):
        candle = candles[index]
        left = candles[index - lookback : index]
        right = candles[index + 1 : index + lookback + 1]

        is_swing_high = all(candle.high > other.high for other in left + right)
        is_swing_low = all(candle.low < other.low for other in left + right)

        if is_swing_high:
            swings.append(SwingPoint(index=index, time=candle.time, price=candle.high, kind="high"))

        if is_swing_low:
            swings.append(SwingPoint(index=index, time=candle.time, price=candle.low, kind="low"))

    return sorted(swings, key=lambda swing: swing.index)


def detect_bos_events(
    candles: Iterable[Candle | Mapping[str, object]],
    *,
    swing_lookback: int = 2,
    major_swing_lookback: int = 5,
    close_confirmation: bool = True,
    volume_period: int = 20,
    volume_multiplier: float = 1.2,
    retest_window: int = 5,
    reversal_window: int = 3,
    risk_reward_target: float = 2.0,
    require_body_close: bool = True,
    require_displacement: bool = True,
    displacement_period: int = 10,
    displacement_multiplier: float = 1.25,
    higher_timeframe_bias: Optional[BOSDirection] = None,
) -> list[BOSEvent]:
    """
    Detect BOS events from OHLCV candles.

    Rules implemented from the markdown:
    - Bullish BOS: price closes above a previous swing high.
    - Bearish BOS: price closes below a previous swing low.
    - Internal BOS: minor swing broken inside broader structure.
    - External BOS: major swing broken, confirming broader directional change.
    - Liquidity BOS: price sweeps a swing but closes back through it sharply.
    - Valid BOS: body close beyond structure plus displacement/momentum.
    - Weak BOS: body close beyond structure without enough displacement.
    - Fake BOS: break is immediately reversed.
    - CHOCH: external break against the supplied higher-timeframe bias.
    """
    series = normalize_candles(candles)
    if len(series) < max(swing_lookback, major_swing_lookback) * 2 + 1:
        return []

    internal_swings = find_swing_points(series, lookback=swing_lookback)
    external_swings = find_swing_points(series, lookback=major_swing_lookback)
    external_keys = {(swing.index, swing.kind) for swing in external_swings}

    events: list[BOSEvent] = []
    broken_swings: set[tuple[int, str]] = set()

    for index, candle in enumerate(series):
        prior_swings = [swing for swing in internal_swings if swing.index < index]

        for swing in prior_swings:
            swing_key = (swing.index, swing.kind)
            if swing_key in broken_swings:
                continue

            direction = _break_direction(candle, swing, close_confirmation)
            wick_direction = _wick_break_direction(candle, swing)
            liquidity_direction = _liquidity_sweep_direction(candle, swing)

            if direction is None and wick_direction is None and liquidity_direction is None:
                continue

            broken_swings.add(swing_key)
            final_direction = direction or liquidity_direction or wick_direction
            assert final_direction is not None

            is_liquidity = direction is None and liquidity_direction is not None
            bos_type = _classify_bos(
                swing=swing,
                swing_key=swing_key,
                external_keys=external_keys,
                is_liquidity_bos=is_liquidity,
            )
            body_close_confirmed = _body_close_confirmed(candle, swing, final_direction)
            displacement_confirmed = _displacement_confirmed(
                series=series,
                index=index,
                period=displacement_period,
                multiplier=displacement_multiplier,
            )
            volume_confirmed = _volume_confirmed(
                series=series,
                index=index,
                period=volume_period,
                multiplier=volume_multiplier,
            )
            retest_confirmed = _retest_confirmed(
                series=series,
                start_index=index,
                level=swing.price,
                direction=final_direction,
                window=retest_window,
            )
            reversal_confirmed = _reversal_confirmed(
                series=series,
                start_index=index,
                level=swing.price,
                direction=final_direction,
                window=reversal_window,
            )
            timeframe_conflict = (
                higher_timeframe_bias is not None and final_direction != higher_timeframe_bias
            )
            signal = _structure_signal(
                bos_type=bos_type,
                body_close_confirmed=body_close_confirmed,
                reversal_confirmed=reversal_confirmed,
                wick_direction=wick_direction,
                liquidity_direction=liquidity_direction,
                timeframe_conflict=timeframe_conflict,
            )
            validation_status, rejection_reason = _validation_status(
                signal=signal,
                body_close_confirmed=body_close_confirmed,
                displacement_confirmed=displacement_confirmed,
                require_body_close=require_body_close,
                require_displacement=require_displacement,
                timeframe_conflict=timeframe_conflict,
            )
            stop_loss = _stop_loss(series, index, final_direction, swing.price)
            take_profit = _take_profit(candle.close, stop_loss, final_direction, risk_reward_target)
            event_rr = _risk_reward(candle.close, stop_loss, take_profit)

            events.append(
                BOSEvent(
                    index=index,
                    time=candle.time,
                    direction=final_direction,
                    bos_type=bos_type,
                    broken_swing=swing,
                    break_price=swing.price,
                    close_price=candle.close,
                    signal=signal,
                    validation_status=validation_status,
                    body_close_confirmed=body_close_confirmed,
                    displacement_confirmed=displacement_confirmed,
                    volume_confirmed=volume_confirmed,
                    retest_confirmed=retest_confirmed,
                    reversal_confirmed=reversal_confirmed,
                    timeframe_conflict=timeframe_conflict,
                    rejection_reason=rejection_reason,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward=event_rr,
                )
            )

    return events


def latest_confirmed_bos(
    candles: Iterable[Candle | Mapping[str, object]],
    **kwargs: object,
) -> Optional[BOSEvent]:
    """Return the latest BOS with both volume and retest confirmation."""
    events = detect_bos_events(candles, **kwargs)
    confirmed = [
        event
        for event in events
        if event.signal == StructureSignal.BOS
        and event.validation_status == ValidationStatus.VALID
        and event.volume_confirmed
        and event.retest_confirmed
    ]
    return confirmed[-1] if confirmed else None


def build_bos_validation_scenarios() -> list[TestScenario]:
    """
    Build a practical test mix:
    - 30% clean textbook BOS
    - 40% messy real-market BOS
    - 20% fake BOS / liquidity grabs
    - 10% edge cases
    """
    return [
        _scenario(
            "clean_strong_bullish_bos_with_displacement",
            "clean_textbook_bos",
            StructureSignal.BOS,
            ValidationStatus.VALID,
            [100, 103, 106, 102, 98, 99, 108, 106.4, 110],
            volumes=[1000, 1050, 1100, 900, 950, 980, 1900, 1400, 1500],
        ),
        _scenario(
            "clean_bearish_bos_with_body_close",
            "clean_textbook_bos",
            StructureSignal.BOS,
            ValidationStatus.VALID,
            [110, 107, 104, 108, 112, 109, 101, 103, 99],
            volumes=[1000, 1030, 1080, 900, 920, 980, 1850, 1300, 1450],
        ),
        _scenario(
            "bos_after_consolidation",
            "clean_textbook_bos",
            StructureSignal.BOS,
            ValidationStatus.VALID,
            [100, 102, 101, 103, 102, 101, 104, 108, 107],
            volumes=[900, 920, 880, 940, 910, 905, 1000, 1700, 1300],
        ),
        _scenario(
            "messy_real_market_bos",
            "messy_real_market_bos",
            StructureSignal.BOS,
            ValidationStatus.VALID,
            [100, 104, 101, 105, 99, 103, 98, 106.5, 104.8, 108.2],
            volumes=[1000, 1150, 900, 1200, 950, 980, 970, 1700, 1250, 1500],
        ),
        _scenario(
            "internal_bos_inside_range",
            "messy_real_market_bos",
            StructureSignal.BOS,
            ValidationStatus.WEAK,
            [100, 105, 101, 104, 102, 105.2, 103, 104.8, 102],
            volumes=[1000, 1100, 900, 980, 930, 1010, 970, 960, 940],
        ),
        _scenario(
            "high_volume_impulsive_bos",
            "messy_real_market_bos",
            StructureSignal.BOS,
            ValidationStatus.VALID,
            [100, 102, 106, 101, 99, 100, 109.5, 108.5, 111],
            volumes=[900, 940, 980, 860, 870, 890, 2600, 1800, 1600],
        ),
        _scenario(
            "bos_inside_channel_pattern",
            "messy_real_market_bos",
            StructureSignal.BOS,
            ValidationStatus.WEAK,
            [100, 102, 104, 103, 105, 104, 106.2, 105.5, 107],
            volumes=[1000, 1010, 1020, 990, 1005, 980, 1040, 1000, 1010],
        ),
        _scenario(
            "wick_break_only_rejected",
            "fake_bos_liquidity_grab",
            StructureSignal.WICK_BREAK,
            ValidationStatus.REJECTED,
            [100, 103, 106, 102, 99, 100, 105.4, 101],
            highs=[101, 104, 106, 103, 100, 101, 107.2, 102],
            volumes=[1000, 1050, 1100, 900, 950, 980, 1200, 1250],
        ),
        _scenario(
            "bos_immediately_followed_by_reversal",
            "fake_bos_liquidity_grab",
            StructureSignal.FAKE_BOS,
            ValidationStatus.REJECTED,
            [100, 103, 106, 102, 99, 100, 107, 101, 98],
            volumes=[1000, 1050, 1100, 900, 950, 980, 1700, 1800, 1600],
        ),
        _scenario(
            "bos_after_liquidity_sweep",
            "edge_case",
            StructureSignal.LIQUIDITY_GRAB,
            ValidationStatus.REJECTED,
            [100, 103, 106, 102, 99, 100, 105.2, 108],
            highs=[101, 104, 106, 103, 100, 101, 107.5, 109],
            volumes=[1000, 1050, 1100, 900, 950, 980, 1650, 1800],
        ),
    ]


def _break_direction(
    candle: Candle,
    swing: SwingPoint,
    close_confirmation: bool,
) -> Optional[BOSDirection]:
    if swing.kind == "high":
        broke = candle.close > swing.price if close_confirmation else candle.high > swing.price
        return BOSDirection.BULLISH if broke else None

    broke = candle.close < swing.price if close_confirmation else candle.low < swing.price
    return BOSDirection.BEARISH if broke else None


def _body_close_confirmed(
    candle: Candle,
    swing: SwingPoint,
    direction: BOSDirection,
) -> bool:
    body_high = max(candle.open, candle.close)
    body_low = min(candle.open, candle.close)

    if direction == BOSDirection.BULLISH and swing.kind == "high":
        return body_high > swing.price and candle.close > swing.price

    if direction == BOSDirection.BEARISH and swing.kind == "low":
        return body_low < swing.price and candle.close < swing.price

    return False


def _wick_break_direction(candle: Candle, swing: SwingPoint) -> Optional[BOSDirection]:
    if swing.kind == "high" and candle.high > swing.price and candle.close <= swing.price:
        return BOSDirection.BULLISH

    if swing.kind == "low" and candle.low < swing.price and candle.close >= swing.price:
        return BOSDirection.BEARISH

    return None


def _liquidity_sweep_direction(candle: Candle, swing: SwingPoint) -> Optional[BOSDirection]:
    if swing.kind == "high" and candle.high > swing.price and candle.close < swing.price:
        return BOSDirection.BEARISH

    if swing.kind == "low" and candle.low < swing.price and candle.close > swing.price:
        return BOSDirection.BULLISH

    return None


def _displacement_confirmed(
    series: Sequence[Candle],
    index: int,
    period: int,
    multiplier: float,
) -> bool:
    if period <= 0:
        return True

    start = max(0, index - period)
    prior_ranges = [candle.high - candle.low for candle in series[start:index]]
    prior_bodies = [abs(candle.close - candle.open) for candle in series[start:index]]
    if not prior_ranges or not prior_bodies:
        return False

    candle = series[index]
    current_range = candle.high - candle.low
    current_body = abs(candle.close - candle.open)
    average_range = sum(prior_ranges) / len(prior_ranges)
    average_body = sum(prior_bodies) / len(prior_bodies)
    body_ratio = current_body / current_range if current_range else 0.0

    return (
        current_range >= average_range * multiplier
        and current_body >= average_body * multiplier
        and body_ratio >= 0.55
    )


def _classify_bos(
    swing: SwingPoint,
    swing_key: tuple[int, str],
    external_keys: set[tuple[int, str]],
    is_liquidity_bos: bool,
) -> BOSType:
    if is_liquidity_bos:
        return BOSType.LIQUIDITY

    if swing_key in external_keys:
        return BOSType.EXTERNAL

    return BOSType.INTERNAL


def _volume_confirmed(
    series: Sequence[Candle],
    index: int,
    period: int,
    multiplier: float,
) -> bool:
    if period <= 0 or index == 0:
        return True

    start = max(0, index - period)
    sample = [candle.volume for candle in series[start:index] if candle.volume > 0]
    if not sample or series[index].volume <= 0:
        return False

    average_volume = sum(sample) / len(sample)
    return series[index].volume >= average_volume * multiplier


def _retest_confirmed(
    series: Sequence[Candle],
    start_index: int,
    level: float,
    direction: BOSDirection,
    window: int,
) -> bool:
    if window <= 0:
        return False

    future = series[start_index + 1 : start_index + 1 + window]
    for candle in future:
        if direction == BOSDirection.BULLISH and candle.low <= level <= candle.close:
            return True
        if direction == BOSDirection.BEARISH and candle.high >= level >= candle.close:
            return True

    return False


def _reversal_confirmed(
    series: Sequence[Candle],
    start_index: int,
    level: float,
    direction: BOSDirection,
    window: int,
) -> bool:
    if window <= 0:
        return False

    future = series[start_index + 1 : start_index + 1 + window]
    for candle in future:
        if direction == BOSDirection.BULLISH and candle.close < level:
            return True
        if direction == BOSDirection.BEARISH and candle.close > level:
            return True

    return False


def _structure_signal(
    bos_type: BOSType,
    body_close_confirmed: bool,
    reversal_confirmed: bool,
    wick_direction: Optional[BOSDirection],
    liquidity_direction: Optional[BOSDirection],
    timeframe_conflict: bool,
) -> StructureSignal:
    if liquidity_direction is not None and not body_close_confirmed:
        return StructureSignal.LIQUIDITY_GRAB

    if wick_direction is not None and not body_close_confirmed:
        return StructureSignal.WICK_BREAK

    if reversal_confirmed:
        return StructureSignal.FAKE_BOS

    if timeframe_conflict and bos_type == BOSType.EXTERNAL:
        return StructureSignal.CHOCH

    return StructureSignal.BOS


def _validation_status(
    signal: StructureSignal,
    body_close_confirmed: bool,
    displacement_confirmed: bool,
    require_body_close: bool,
    require_displacement: bool,
    timeframe_conflict: bool,
) -> tuple[ValidationStatus, Optional[str]]:
    if signal in {
        StructureSignal.WICK_BREAK,
        StructureSignal.FAKE_BOS,
        StructureSignal.LIQUIDITY_GRAB,
    }:
        return ValidationStatus.REJECTED, signal.value

    if require_body_close and not body_close_confirmed:
        return ValidationStatus.REJECTED, "missing_body_close"

    if timeframe_conflict:
        return ValidationStatus.WEAK, "higher_timeframe_conflict"

    if require_displacement and not displacement_confirmed:
        return ValidationStatus.WEAK, "weak_or_missing_displacement"

    return ValidationStatus.VALID, None


def _stop_loss(
    series: Sequence[Candle],
    index: int,
    direction: BOSDirection,
    broken_level: float,
    lookback: int = 5,
) -> float:
    recent = series[max(0, index - lookback) : index + 1]
    if direction == BOSDirection.BULLISH:
        return min(min(candle.low for candle in recent), broken_level)

    return max(max(candle.high for candle in recent), broken_level)


def _take_profit(
    entry: float,
    stop_loss: Optional[float],
    direction: BOSDirection,
    risk_reward_target: float,
) -> Optional[float]:
    if stop_loss is None:
        return None

    risk = abs(entry - stop_loss)
    if risk == 0:
        return None

    if direction == BOSDirection.BULLISH:
        return entry + risk * risk_reward_target

    return entry - risk * risk_reward_target


def _risk_reward(
    entry: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> Optional[float]:
    if stop_loss is None or take_profit is None:
        return None

    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    return None if risk == 0 else reward / risk


def _scenario(
    name: str,
    category: str,
    expected_signal: StructureSignal,
    expected_status: ValidationStatus,
    closes: list[float],
    *,
    highs: Optional[list[float]] = None,
    lows: Optional[list[float]] = None,
    volumes: Optional[list[float]] = None,
) -> TestScenario:
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        previous_close = closes[index - 1] if index else close
        open_price = previous_close
        high = highs[index] if highs else (close + 0.8 if close >= open_price else open_price + 0.1)
        low = lows[index] if lows else (close - 0.8 if close <= open_price else open_price - 0.1)
        volume = volumes[index] if volumes else 1000.0
        candles.append(
            Candle(
                time=index,
                open=float(open_price),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )
        )

    return TestScenario(
        name=name,
        category=category,
        expected_signal=expected_signal,
        expected_status=expected_status,
        candles=candles,
    )


if __name__ == "__main__":
    example_candles = [
        {"time": "09:15", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
        {"time": "09:20", "open": 101, "high": 104, "low": 100, "close": 103, "volume": 1050},
        {"time": "09:25", "open": 103, "high": 106, "low": 102, "close": 105, "volume": 1100},
        {"time": "09:30", "open": 105, "high": 105, "low": 101, "close": 102, "volume": 900},
        {"time": "09:35", "open": 102, "high": 103, "low": 98, "close": 99, "volume": 950},
        {"time": "09:40", "open": 99, "high": 100, "low": 97, "close": 98, "volume": 980},
        {"time": "09:45", "open": 98, "high": 107, "low": 98, "close": 106.5, "volume": 1800},
        {"time": "09:50", "open": 106.5, "high": 107, "low": 105.8, "close": 106.2, "volume": 1300},
    ]

    for bos in detect_bos_events(
        example_candles,
        swing_lookback=1,
        major_swing_lookback=2,
        volume_period=3,
        displacement_period=3,
    ):
        print(bos)
