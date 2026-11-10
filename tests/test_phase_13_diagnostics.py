import pytest
from modules.strategy_selector import MasterStrategySelector


def test_funnel_dict_initialized():
    sel = MasterStrategySelector()
    assert hasattr(sel, "funnel"), "funnel dict missing"
    # Touch a key to trigger defaultdict
    sel.funnel["TEST"]["offered"] += 1
    assert sel.funnel["TEST"]["offered"] == 1
    assert sel.funnel["TEST"]["won"] == 0


def test_funnel_report_runs():
    sel = MasterStrategySelector()
    sel.funnel["VWAP_BOUNCE"]["offered"] = 100
    sel.funnel["VWAP_BOUNCE"]["won"] = 50
    out = sel.funnel_report()
    assert "VWAP_BOUNCE" in out
    assert "100" in out
    assert "50" in out


def test_reset_funnel():
    sel = MasterStrategySelector()
    sel.funnel["ABC"]["offered"] = 5
    sel.reset_funnel()
    assert sel.funnel["ABC"]["offered"] == 0
