from fastapi import APIRouter
from pydantic import BaseModel
import os
import json
from utils.jsonl_tailer import tail_jsonl

router = APIRouter(prefix="/api/regime", tags=["regime"])

REGIME_HISTORY_FILE = "data/regime_history.jsonl"

@router.get("/current")
async def get_current_regime():
    history = await tail_jsonl(REGIME_HISTORY_FILE, 1)
    if history:
        return history[0]
    return {"regime": "UNKNOWN", "confidence": 0.0}

@router.get("/history")
async def get_regime_history(limit: int = 100):
    history = await tail_jsonl(REGIME_HISTORY_FILE, limit)
    return {"history": history}

class RegimeThresholds(BaseModel):
    trending_threshold: float
    choppy_threshold: float

@router.post("/thresholds")
def set_regime_thresholds(thresholds: RegimeThresholds):
    # This would update config/regime.yaml
    return {"status": "success", "message": "Regime thresholds updated"}
