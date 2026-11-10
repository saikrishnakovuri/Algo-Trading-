from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import asyncio
import os

router = APIRouter(prefix="/api/logs", tags=["logs"])

LOG_FILE = "logs/options_bot.log"

@router.get("/tail")
def tail_logs(lines: int = 100):
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    
    with open(LOG_FILE, 'r') as f:
        content = f.readlines()
        return {"logs": content[-lines:]}

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    if not os.path.exists(LOG_FILE):
        await websocket.send_text("Log file not found")
        await websocket.close()
        return
        
    try:
        with open(LOG_FILE, 'r') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Log WebSocket error: {e}")
