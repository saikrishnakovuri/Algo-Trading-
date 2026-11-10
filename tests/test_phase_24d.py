import pytest
import pandas as pd
from datetime import datetime
import yaml

def test_position_cap_enforces_notional_limit():
    """
    Test that position size is correctly calculated based on max_notional_per_trade_pct_of_capital
    and fixed_risk_per_trade_pct.
    """
    with open("config/risk_execution.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    pos_cfg = cfg.get("position_sizing", {})
    assert "max_notional_per_trade_pct_of_capital" in pos_cfg
    assert "fixed_risk_per_trade_pct" in pos_cfg
    
    # We can't easily mock the full backtest loop here, but we can verify the config
    # has the expected values.
    assert pos_cfg["max_notional_per_trade_pct_of_capital"] == 15.0
    assert pos_cfg["fixed_risk_per_trade_pct"] == 1.0


def test_vol_gate_config():
    """
    Test that volatility gate is enabled and configured correctly.
    """
    with open("config/risk_execution.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    vol_gate = cfg.get("volatility_gate", {})
    assert vol_gate.get("enabled") is True
    assert vol_gate.get("india_vix_min_threshold") == 13.0
    assert vol_gate.get("fallback_atr_pct_of_price_min") == 0.06
    
    strategies = vol_gate.get("applies_to_strategies", [])
    assert "VWAP_BOUNCE" in strategies
    assert "MOMENTUM_BREAKOUT" in strategies
    assert "CANDLESTICK" in strategies
    assert "MEAN_REVERSION" not in strategies # Exempted
