import pandas as pd

from modules.momentum_engine import MomentumBreakoutEngine
from modules.strategy_selector import MasterStrategySelector


class _Ctx:
    regime = "TRENDING_UP"


def _momentum_df():
    rows = []
    for i in range(8):
        rows.append({"open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 110 + i, "volume": 100})
    rows.append({"open": 115.0, "high": 127.0, "low": 114.8, "close": 126.0, "volume": 112})
    return pd.DataFrame(rows)


def test_strict_momentum_rejects_relaxed_breakout():
    engine = MomentumBreakoutEngine()
    df = _momentum_df()
    consolidation = [{"high": 125.0, "low": 98.0, "bars": 6, "volume_avg": 100.0, "end_idx": 7}]

    result = engine.detect_breakout(df, consolidation, len(df) - 1, config=None)

    assert result["signal"] is None


def test_participation_momentum_accepts_relaxed_breakout():
    engine = MomentumBreakoutEngine()
    df = _momentum_df()
    consolidation = [{"high": 125.0, "low": 98.0, "bars": 6, "volume_avg": 100.0, "end_idx": 7}]

    result = engine.detect_breakout(
        df,
        consolidation,
        len(df) - 1,
        config={
            "participation_mode": True,
            "volume_breakout_ratio": 1.10,
            "body_impulse_ratio": 1.05,
            "use_slope_confirmation": True,
        },
    )

    assert result["signal"] == "LONG"
    assert result["setup_type"] == "PARTICIPATION_BREAKOUT"
    assert result["score"] < 5.0


def test_selector_adds_momentum_only_for_participation_modes():
    selector = MasterStrategySelector()
    base = []

    normal = selector._augment_candidates_for_participation(base, _Ctx(), "NORMAL")
    balanced = selector._augment_candidates_for_participation(base, _Ctx(), "BALANCED")

    assert normal == []
    assert [c.name for c in balanced] == ["MOMENTUM_BREAKOUT"]
    assert balanced[0].risk_multiplier < 0.5
