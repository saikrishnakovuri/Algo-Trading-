import pytest
from datetime import datetime, timedelta
from modules.risk_guard import RiskGuard, IST
from modules.v3_utils import TOTAL_CAPITAL

def test_risk_guard_ist_rollover():
    """REQ 25a-9: Test daily rollover based on IST."""
    guard = RiskGuard(starting_capital=TOTAL_CAPITAL)
    guard.reset()
    
    # 1. Trade late at night IST (e.g., 23:00 IST = 17:30 UTC)
    t1 = datetime(2026, 5, 12, 23, 0).replace(tzinfo=IST)
    guard.record_trade(pnl=-1000.0, now=t1)
    assert guard.day_pnl == -1000.0
    
    # 2. Trade early next morning IST (e.g., 01:00 IST = 19:30 UTC previous day)
    t2 = datetime(2026, 5, 13, 1, 0).replace(tzinfo=IST)
    allowed, reason = guard.can_trade(now=t2)
    assert guard.day_pnl == 0.0 # Should have rolled over
    assert allowed is True

def test_risk_guard_limits():
    """Test if limits are respected."""
    guard = RiskGuard(starting_capital=100000.0, daily_loss_pct=1.0)
    guard.reset()
    
    now = datetime.now(IST)
    guard.record_trade(pnl=-1500.0, now=now) # Exceeds 1% limit
    
    allowed, reason = guard.can_trade(now=now)
    assert allowed is False
    assert "DAILY_LOSS" in reason

if __name__ == "__main__":
    pytest.main([__file__])
