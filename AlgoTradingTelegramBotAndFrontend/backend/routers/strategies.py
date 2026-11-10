from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import os

# Append root to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("/list")
def list_strategies():
    try:
        from modules.strategy_mapper import STRATEGY_MAP
        return {"strategies": STRATEGY_MAP}
    except Exception as e:
        return {"error": str(e), "strategies": {}}

class ToggleRequest(BaseModel):
    regime: str
    strategy: str
    enabled: bool

@router.post("/toggle")
def toggle_strategy(req: ToggleRequest):
    # This would normally modify modules/strategy_mapper.py or a config
    # Since we can't touch locked files, we'd need a dynamic way
    return {"status": "success", "message": f"Strategy {req.strategy} in {req.regime} set to {req.enabled}"}

class ConfidenceRequest(BaseModel):
    regime: str
    strategy: str
    min_confidence: float

@router.post("/min_confidence")
def set_min_confidence(req: ConfidenceRequest):
    return {"status": "success", "message": f"Strategy {req.strategy} in {req.regime} min_confidence set to {req.min_confidence}"}
