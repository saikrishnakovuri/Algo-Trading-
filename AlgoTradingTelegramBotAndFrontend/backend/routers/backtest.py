from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import uuid
import json
from datetime import datetime
from utils.subprocess_runner import SubprocessManager

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

RESULTS_DIR = "reports"
HISTORY_FILE = "data/backtest_history.jsonl"

class BacktestRequest(BaseModel):
    start_date: str
    end_date: str
    symbol: str = "NIFTY"
    capital: float = 100000.0
    risk_pct: float = 1.0

@router.post("/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    # Command to run main_backtest.py
    # Assuming main_backtest.py takes args
    command = f"python main_backtest.py --start {request.start_date} --end {request.end_date} --symbol {request.symbol} --capital {request.capital} --risk {request.risk_pct} --job_id {job_id}"
    
    success, message = SubprocessManager.start_process(f"backtest_{job_id}", command)
    
    if success:
        # Save to history
        os.makedirs("data", exist_ok=True)
        with open(HISTORY_FILE, "a") as f:
            f.write(json.dumps({
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "request": request.dict(),
                "status": "running"
            }) + "\n")
        return {"job_id": job_id, "message": "Backtest started"}
    else:
        raise HTTPException(status_code=500, detail=message)

@router.get("/status/{job_id}")
def get_status(job_id: str):
    status = SubprocessManager.get_status(f"backtest_{job_id}")
    return {"job_id": job_id, "status": status}

@router.get("/result/{job_id}")
def get_result(job_id: str):
    # Search for result file in RESULTS_DIR
    # Assuming result is saved as {job_id}.json or similar
    result_path = os.path.join(RESULTS_DIR, f"result_{job_id}.json")
    if os.path.exists(result_path):
        with open(result_path, 'r') as f:
            return json.load(f)
    else:
        # Check if it's still running
        if SubprocessManager.is_running(f"backtest_{job_id}"):
            return {"job_id": job_id, "status": "running"}
        else:
            raise HTTPException(status_code=404, detail="Result not found")

@router.get("/history")
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return {"history": []}
    
    history = []
    with open(HISTORY_FILE, 'r') as f:
        for line in f:
            history.append(json.loads(line))
    return {"history": history}
