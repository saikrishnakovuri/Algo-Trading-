import asyncio
import random
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from utils.candle_manager import candle_manager

# Import necessary modules
try:
    from modules.broker_layer import AngelOneBroker
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from modules.broker_layer import AngelOneBroker

router = APIRouter(prefix="/api/candles", tags=["candles"])

# Active simulation state
SIMULATION_STATE = {
    "NIFTY": {"price": 22605.50, "open": 22605.50, "last_time": datetime.now(), "bucket": 0},
    "BANKNIFTY": {"price": 48200.15, "open": 48200.15, "last_time": datetime.now(), "bucket": 0},
    "FINNIFTY": {"price": 21450.00, "open": 21450.00, "last_time": datetime.now(), "bucket": 0}
}

async def candle_broadcaster():
    """Background task to generate and broadcast mock candles every 1 second."""
    while True:
        try:
            now = datetime.now()
            for symbol, state in SIMULATION_STATE.items():
                # Align time to 5-minute buckets
                bucket_start = now.replace(second=0, microsecond=0)
                bucket_start -= timedelta(minutes=now.minute % 5)
                bucket_ts = int(bucket_start.timestamp())
                
                # If new bucket, reset open price
                if bucket_ts != state["bucket"]:
                    state["open"] = state["price"]
                    state["bucket"] = bucket_ts

                # Random price movement
                change = random.uniform(-1.5, 1.5)
                state["price"] += change
                
                candle = {
                    "type": "candle",
                    "symbol": symbol,
                    "timeframe": "5m",
                    "time": bucket_ts,
                    "open": round(state["open"], 2),
                    "high": round(max(state["open"], state["price"] + random.uniform(0, 2)), 2),
                    "low": round(min(state["open"], state["price"] - random.uniform(0, 2)), 2),
                    "close": round(state["price"], 2),
                    "volume": random.randint(100, 500),
                    "timestamp": int(now.timestamp())
                }
                await candle_manager.broadcast(candle)
            
            await asyncio.sleep(1) # 1 second frequency
        except Exception as e:
            print(f"Broadcaster error: {e}")
            await asyncio.sleep(5)

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(candle_broadcaster())

@router.websocket("/ws/live-candles")
async def websocket_candles(websocket: WebSocket):
    await websocket.accept()
    candle_manager.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        candle_manager.unregister(websocket)

@router.get("/history")
async def get_candle_history(
    symbol: str = Query(..., description="Symbol to fetch history for"),
    timeframe: str = Query("5m", description="Timeframe"),
    limit: int = Query(500, le=1000)
):
    """
    Returns historical candle data. 
    Uses AngelOneBroker for real NIFTY/BANKNIFTY data.
    """
    if symbol in ["NIFTY", "BANKNIFTY"]:
        try:
            broker = AngelOneBroker()
            if broker.login():
                tokens = {
                    "NIFTY": "99926000",
                    "BANKNIFTY": "99926009"
                }
                token = tokens.get(symbol)
                interval_map = {
                    "1m": "ONE_MINUTE", 
                    "5m": "FIVE_MINUTE", 
                    "15m": "FIFTEEN_MINUTE", 
                    "1h": "ONE_HOUR", 
                    "1d": "ONE_DAY"
                }
                interval = interval_map.get(timeframe, "FIVE_MINUTE")
                
                # For 1m/5m, 2 days is plenty for a 500 limit
                days = 2 if timeframe in ["1m", "5m"] else 30
                
                df = broker.get_historical_data(symbol, token, interval=interval, days=days)
                if df is not None and not df.empty:
                    history = []
                    for idx, row in df.iterrows():
                        history.append({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "time": int(idx.timestamp()),
                            "open": round(float(row["Open"]), 2),
                            "high": round(float(row["High"]), 2),
                            "low": round(float(row["Low"]), 2),
                            "close": round(float(row["Close"]), 2),
                            "volume": int(row["Volume"]) if "Volume" in row else 0
                        })
                    
                    if history:
                        SIMULATION_STATE[symbol]["price"] = history[-1]["close"]
                        
                    return history[-limit:]
        except Exception as e:
            print(f"Error fetching real {symbol} history from AngelOne: {e}")

    # Fallback to mock data
    history = []
    now = datetime.now()
    tf_minutes = 5
    if timeframe == "1m": tf_minutes = 1
    elif timeframe == "15m": tf_minutes = 15
    elif timeframe == "1h": tf_minutes = 60
    elif timeframe == "1D": tf_minutes = 1440
    
    start_time = now - timedelta(minutes=tf_minutes * limit)
    price = 22000.0 if "NIFTY" in symbol else 48000.0 if "BANK" in symbol else 1000.0
    
    for i in range(limit):
        candle_time = start_time + timedelta(minutes=tf_minutes * i)
        change = random.uniform(-10, 10)
        open_p = price
        high_p = open_p + random.uniform(0, 15)
        low_p = open_p - random.uniform(0, 15)
        close_p = open_p + change
        
        history.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "time": int(candle_time.timestamp()),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": random.randint(1000, 5000)
        })
        price = close_p
    return history
