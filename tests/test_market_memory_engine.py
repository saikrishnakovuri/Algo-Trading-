import pandas as pd

from modules.market_memory_engine import (
    HIGH_MANIPULATION_RISK,
    INVALIDATED,
    PENDING_BODY_CLOSE,
    READY,
    WAITING_RETEST,
    MarketMemoryEngine,
)


def _frame(rows):
    return pd.DataFrame(rows, index=pd.date_range("2026-01-01 09:15", periods=len(rows), freq="1min"))


def test_retest_failure_reclaim_invalidates_waiting_setup():
    memory = MarketMemoryEngine(max_pending_bars=15, max_retest_bars=15)
    memory.ingest_events(
        "NIFTY",
        [{
            "type": "body_close",
            "direction": "BULL",
            "level": 24500,
            "invalidation_level": 24450,
            "bar_idx": 0,
            "source": "TEST_BOS",
        }],
        current_idx=0,
    )

    memory.update("NIFTY", _frame([
        {"open": 24520, "high": 24540, "low": 24480, "close": 24490},
    ]))

    assert not memory.active_setups("NIFTY")
    assert memory.completed[-1].state == INVALIDATED
    assert "structure_reclaimed" in memory.completed[-1].reasons
    assert memory.history["NIFTY"]["last_failed_retest"]["level"] == 24500


def test_double_sweep_sets_manipulation_risk_veto():
    memory = MarketMemoryEngine(double_sweep_window_bars=10)
    memory.ingest_events(
        "NIFTY",
        [{"type": "wick_break", "direction": "BULL", "level": 24600, "bar_idx": 10}],
        current_idx=10,
    )
    memory.ingest_events(
        "NIFTY",
        [{"type": "wick_break", "direction": "BEAR", "level": 24400, "bar_idx": 15}],
        current_idx=15,
    )

    assert memory.is_manipulation_risk("NIFTY", current_idx=15)
    assert memory.manipulation_reason("NIFTY") == HIGH_MANIPULATION_RISK
    assert memory.manipulation_weight("NIFTY") >= 0.90
    assert not memory.should_veto_for_manipulation("NIFTY", current_idx=15)


def test_narrative_weighting_respects_event_overrides():
    memory = MarketMemoryEngine(double_sweep_window_bars=10, manipulation_veto_weight=0.80)
    memory.ingest_events(
        "NIFTY",
        [{"type": "wick_break", "direction": "BULL", "level": 24600, "bar_idx": 10, "weight": 0.20}],
        current_idx=10,
    )
    memory.ingest_events(
        "NIFTY",
        [{"type": "wick_break", "direction": "BEAR", "level": 24400, "bar_idx": 19, "weight": 0.25}],
        current_idx=19,
    )

    assert memory.is_manipulation_risk("NIFTY", current_idx=19)
    assert not memory.should_veto_for_manipulation("NIFTY", current_idx=19)
    assert memory.manipulation_weight("NIFTY") < 0.80


def test_minor_internal_bos_has_lower_default_weight_than_double_sweep():
    memory = MarketMemoryEngine()
    memory.ingest_events(
        "NIFTY",
        [{"type": "minor_internal_bos", "direction": "BULL", "level": 100, "bar_idx": 1}],
        current_idx=1,
    )

    state = memory.narrative_state("NIFTY")
    setup = memory.active_setups("NIFTY")[0]
    assert setup.metadata["weight"] == 0.41
    assert state.active_setups[setup.setup_id].metadata["weight"] == 0.41


def test_sequential_memory_persists_from_wick_to_retest():
    memory = MarketMemoryEngine(max_pending_bars=15, max_retest_bars=15)
    memory.ingest_events(
        "NIFTY",
        [{
            "type": "wick_break",
            "direction": "BULL",
            "level": 102,
            "invalidation_level": 99,
            "bar_idx": 0,
        }],
        current_idx=0,
    )

    assert memory.active_setups("NIFTY")[0].state == PENDING_BODY_CLOSE

    memory.update("NIFTY", _frame([
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 100, "high": 103, "low": 100, "close": 102.5},
    ]))
    assert memory.active_setups("NIFTY")[0].state == WAITING_RETEST

    memory.update("NIFTY", _frame([
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 100, "high": 103, "low": 100, "close": 102.5},
        {"open": 102.5, "high": 103, "low": 101.8, "close": 102.2},
    ]))
    assert memory.active_setups("NIFTY")[0].state == READY
    assert memory.ready_signal("NIFTY", _frame([
        {"open": 102.5, "high": 103, "low": 101.8, "close": 102.2},
    ]))["direction"] == "CE"


def test_market_memory_state_round_trip(tmp_path):
    path = tmp_path / "market_memory_state.json"
    memory = MarketMemoryEngine(max_pending_bars=15, max_retest_bars=15)
    memory.ingest_events(
        "NIFTY",
        [{
            "type": "wick_break",
            "direction": "BULL",
            "level": 102,
            "invalidation_level": 99,
            "bar_idx": 0,
        }],
        current_idx=0,
        timestamp=pd.Timestamp("2026-01-01 09:15"),
    )

    memory.save_state(str(path))

    restored = MarketMemoryEngine()
    assert restored.load_state(str(path)) is True
    setup = restored.active_setups("NIFTY")[0]
    assert setup.level == 102
    assert setup.state == PENDING_BODY_CLOSE
    assert restored.history["NIFTY"]["last_sweep"]["direction"] == "BULL"
