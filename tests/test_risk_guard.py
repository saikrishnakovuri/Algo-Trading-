import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
from modules.risk_guard import RiskGuard, STATE_FILE

@pytest.fixture(autouse=True)
def _clean_state():
    if STATE_FILE.exists(): STATE_FILE.unlink()
    yield
    if STATE_FILE.exists(): STATE_FILE.unlink()

def test_daily_loss_trips():
    # Limit = ₹1500
    g = RiskGuard(starting_capital=50000, daily_loss_pct=3.0)
    now = datetime(2025, 11, 1, 10, 0)
    
    # Trade 1: -₹1000 (Allowed)
    g.record_trade(-1000, now)
    assert g.can_trade(now)[0] is True
    
    # Trade 2: -₹600 (Total -1600 > 1500 limit)
    g.record_trade(-600, now)
    allowed, reason = g.can_trade(now)
    assert not allowed
    assert "DAILY_LOSS" in reason

def test_loss_streak_trips():
    g = RiskGuard(starting_capital=50000, streak_limit=3)
    now = datetime(2025, 11, 1, 10, 0)
    
    g.record_trade(-100, now)
    g.record_trade(-100, now)
    assert g.can_trade(now)[0] is True
    
    g.record_trade(-100, now) # 3rd loss
    allowed, reason = g.can_trade(now)
    assert not allowed
    assert "LOSS_STREAK" in reason

def test_streak_resets_on_win():
    g = RiskGuard(starting_capital=50000, streak_limit=3)
    now = datetime(2025, 11, 1, 10, 0)
    
    g.record_trade(-100, now)
    g.record_trade(-100, now)
    g.record_trade(200, now) # Win resets
    g.record_trade(-100, now)
    assert g.can_trade(now)[0] is True

def test_cooldown_lifts_after_period():
    g = RiskGuard(starting_capital=50000, daily_loss_pct=1.0,
                  cooldown_after_daily=timedelta(hours=1))
    now = datetime(2025, 11, 1, 10, 0)
    
    g.record_trade(-1000, now) # Trips (limit 500)
    assert not g.can_trade(now)[0]
    
    later = now + timedelta(hours=2)
    allowed, _ = g.can_trade(later)
    assert allowed

def test_state_persists_across_instances():
    g1 = RiskGuard(starting_capital=50000, streak_limit=3)
    now = datetime(2025, 11, 1, 10, 0)
    
    g1.record_trade(-100, now)
    g1.record_trade(-100, now)
    g1.record_trade(-100, now) # Trips
    
    assert not g1.can_trade(now)[0]
    
    # New instance
    g2 = RiskGuard(starting_capital=50000, streak_limit=3)
    assert not g2.can_trade(now)[0]
    assert g2.trip_reason == "LOSS_STREAK"
