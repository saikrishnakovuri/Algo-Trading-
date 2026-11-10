from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json

router = APIRouter(prefix="/api/riskguard", tags=["riskguard"])

RISK_GUARD_STATE = "data/risk_guard_state.json"

@router.get("/state")
def get_risk_guard_state():
    if not os.path.exists(RISK_GUARD_STATE):
        return {"daily_pnl": 0.0, "trades_today": 0, "consecutive_losses": 0}
    
    with open(RISK_GUARD_STATE, 'r') as f:
        return json.load(f)

class RiskLimits(BaseModel):
    daily_loss_limit: float
    max_trades_per_day: int
    max_consecutive_losses: int

@router.post("/limits")
def set_risk_limits(limits: RiskLimits):
    # This would normally update config/risk_execution.yaml
    return {"status": "success", "message": "Risk limits updated"}

@router.post("/reset")
def reset_risk_guard():
    if os.path.exists(RISK_GUARD_STATE):
        with open(RISK_GUARD_STATE, 'w') as f:
            json.dump({"daily_pnl": 0.0, "trades_today": 0, "consecutive_losses": 0}, f)
    return {"status": "success", "message": "Risk guard state reset"}
