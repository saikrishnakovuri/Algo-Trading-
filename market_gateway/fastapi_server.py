from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from market_gateway.connection_manager import manager
from market_gateway.schemas import HealthStatus
from datetime import datetime

app = FastAPI()

@app.get("/health")
async def health():
    return HealthStatus(status="OK", timestamp=datetime.now())

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
