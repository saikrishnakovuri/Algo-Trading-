from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import pymongo
import os

router = APIRouter(tags=["pnl"])

# MongoDB connection
client = pymongo.MongoClient(os.getenv("MONGO_URL", "mongodb://localhost:27017/"))
db = client[os.getenv("DB_NAME", "tradealert_db")]
trades_col = db["trades"]
risk_col = db["risk_guard"]

@router.websocket("/ws/live-pnl")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. Base Data
            pnl_data = {
                "timestamp": asyncio.get_event_loop().time(),
                "capital": 500000.0,
                "current_pnl": 0.0,
                "daily_pnl": 0.0,
                "trades_today": 0,
                "active_trades": []
            }

            # 2. Read risk guard state (Realized Daily PnL)
            rg_state = risk_col.find_one({"_id": "current_state"})
            if rg_state:
                pnl_data["daily_pnl"] = round(rg_state.get("daily_pnl", 0.0), 2)
                pnl_data["trades_today"] = rg_state.get("trades_today", 0)
                pnl_data["capital"] = round(rg_state.get("starting_capital", 500000.0) + pnl_data["daily_pnl"], 2)

            # 3. Calculate Floating PnL from Active Trades
            open_trades = list(trades_col.find({"status": "OPEN"}))
            floating_pnl = 0.0
            
            for trade in open_trades:
                # In a real system, we'd fetch LTP for trade['symboltoken']
                # For now, we'll sum up the unrealized PnL reported by the bot if available
                # or just list the trades.
                u_pnl = trade.get("unrealized_pnl", 0.0)
                floating_pnl += u_pnl
                pnl_data["active_trades"].append({
                    "id": str(trade.get("trade_id")),
                    "symbol": trade.get("symbol"),
                    "direction": trade.get("direction"),
                    "qty": trade.get("qty"),
                    "entry": trade.get("entry_price"),
                    "pnl": round(u_pnl, 2)
                })

            pnl_data["current_pnl"] = round(floating_pnl, 2)

            await websocket.send_json(pnl_data)
            await asyncio.sleep(2) # Faster updates for P&L
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Live PnL WebSocket error: {e}")

