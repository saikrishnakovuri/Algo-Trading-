from fastapi import APIRouter, Query
import pymongo
from typing import Optional

router = APIRouter(prefix="/api/trades", tags=["trades"])

# MongoDB connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["tradealert_db"]
trades_col = db["trades"]

@router.get("/live")
async def get_live_trades():
    # Return last 50 open trades
    cursor = trades_col.find({"exit_time": {"$exists": False}}).sort("_id", -1).limit(50)
    return {"trades": list(cursor)}

@router.get("/history")
async def get_trade_history(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = 100
):
    query = {}
    if from_date:
        query["entry_time"] = {"$gte": from_date}
    if to_date:
        query.setdefault("entry_time", {})["$lte"] = to_date

    cursor = trades_col.find(query).sort("_id", -1).limit(limit)
    return {"trades": list(cursor)}
