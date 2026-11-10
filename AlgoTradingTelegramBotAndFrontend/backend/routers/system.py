from fastapi import APIRouter, HTTPException
import os
import json
from utils.subprocess_runner import SubprocessManager

router = APIRouter(prefix="/api/system", tags=["system"])

TRADER_NAME = "live_trader"
TRADER_COMMAND = "python live_options_trader.py"

@router.post("/start")
def start_trader():
    success, message = SubprocessManager.start_process(TRADER_NAME, TRADER_COMMAND)
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

@router.post("/stop")
def stop_trader():
    success, message = SubprocessManager.stop_process(TRADER_NAME)
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

@router.post("/kill-switch")
def kill_switch():
    # Stop trader AND potentially other things like pending orders if we had an API for that
    success, message = SubprocessManager.stop_process(TRADER_NAME)
    # Manual close logic would go here if we could communicate with the bot
    return {"status": "success", "message": "Kill switch activated. Trader stopped."}

@router.get("/status")
def get_status():
    trader_status = SubprocessManager.get_status(TRADER_NAME)
    
    # Check for other system health indicators
    status = {
        "live_trader_running": trader_status == "running",
        "backend_health": "OK",
        "vix_value": 15.5, # Placeholder, should read from live state
        "broker_connected": False # Placeholder
    }
    
    # Try to read live_state.json if it exists
    if os.path.exists("data/live_state.json"):
        try:
            with open("data/live_state.json", 'r') as f:
                ls = json.load(f)
                status.update(ls)
        except:
            pass
            
    return status
