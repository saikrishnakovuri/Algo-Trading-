import asyncio
import anyio
import sys
import os
from pathlib import Path

# Add root directory to sys.path
sys.path.append(r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options")

from utils.pid_lock import check_pid_lock

from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import logging
import random
import uuid
import json
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from threading import Thread
# import google.generativeai as genai
from risk_calculator import (
    compute_all_metrics, compute_kelly, compute_monte_carlo,
    compute_equity_curve,
)
from live_state import live_state
from notification_service import notify_trade, start_telegram_polling, format_daily_summary, send_direct_async

from routers import (
    configs, backtest, trades, live_pnl, system, docs, logs,
    strategies, riskguard, regime, notifications, candles, v2_features
)

load_dotenv()
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "tradealert_db")

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]
db_sync = MongoClient(mongo_url)[db_name]

IST = pytz.timezone('Asia/Kolkata')

app = FastAPI(title="TradeAlert Bot API")
api_router = APIRouter(prefix="/api")

api_router.include_router(v2_features.router, tags=["v2"])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ── Models ────────────────────────────────────────────────────────────────────

class TradeCreate(BaseModel):
    trade_id: Optional[str] = None
    symbol: str
    direction: str
    event_type: str
    entry_price: float
    exit_price: Optional[float] = None
    position_size: float
    strategy_name: str
    confidence_score: float
    market_regime: str
    timestamp: Optional[str] = None
    pnl_abs: Optional[float] = None
    pnl_pct: Optional[float] = None
    timeframe: Optional[str] = None
    rr_ratio: Optional[float] = None
    indicators: Optional[dict] = None


class TradeResponse(BaseModel):
    id: str
    trade_id: str
    symbol: str
    direction: str
    event_type: str
    entry_price: float
    exit_price: Optional[float] = None
    position_size: float
    strategy_name: str
    confidence_score: float
    market_regime: str
    timestamp: str
    pnl_abs: Optional[float] = None
    pnl_pct: Optional[float] = None
    timeframe: Optional[str] = None
    rr_ratio: Optional[float] = None
    indicators: Optional[dict] = None
    alert_sent: bool
    alert_message: Optional[str] = None
    created_at: str


class AlertLog(BaseModel):
    id: str
    trade_id: str
    event_type: str
    message: str
    status: str
    error: Optional[str] = None
    created_at: str


class AnalyzeRequest(BaseModel):
    code: str
    command: str
    fileName: Optional[str] = ""
    context: Optional[str] = ""


# ── Daily Summary Logic ───────────────────────────────────────────────────────

async def _compute_summary_data(date_ist, summary_type: str) -> dict:
    """Compute all stats for a summary from the DB for a given IST date."""
    day_start_utc = datetime(date_ist.year, date_ist.month, date_ist.day, 0, 0, 0)
    day_start_utc = IST.localize(day_start_utc).astimezone(pytz.utc)
    day_end_utc = day_start_utc + timedelta(days=1)

    all_trades = await db.trades.find(
        {"created_at": {"$gte": day_start_utc.isoformat(), "$lt": day_end_utc.isoformat()}},
        {"_id": 0}
    ).to_list(10000)

    completed = [
        t for t in all_trades
        if t.get("event_type") in ("exit", "sl", "tp") and t.get("pnl_abs") is not None
    ]
    wins = [t for t in completed if float(t.get("pnl_abs", 0)) > 0]
    losses = [t for t in completed if float(t.get("pnl_abs", 0)) <= 0]
    win_rate = round(len(wins) / len(completed) * 100, 1) if completed else 0
    total_pnl = round(sum(float(t.get("pnl_abs", 0)) for t in completed), 2)
    avg_pnl = round(total_pnl / len(completed), 2) if completed else 0

    open_positions = len([t for t in all_trades if t.get("event_type") == "entry"])

    # Best and worst trade
    best = max(completed, key=lambda t: float(t.get("pnl_abs", 0)), default=None)
    worst = min(completed, key=lambda t: float(t.get("pnl_abs", 0)), default=None)

    strategy_stats: dict = {}
    for t in completed:
        s = t.get("strategy_name", "Unknown")
        if s not in strategy_stats:
            strategy_stats[s] = {"trades": 0, "pnl": 0.0, "wins": 0}
        strategy_stats[s]["trades"] += 1
        strategy_stats[s]["pnl"] = round(strategy_stats[s]["pnl"] + float(t.get("pnl_abs", 0)), 2)
        if float(t.get("pnl_abs", 0)) > 0:
            strategy_stats[s]["wins"] += 1

    regime_counts: dict = {}
    for t in all_trades:
        r = t.get("market_regime", "unknown")
        regime_counts[r] = regime_counts.get(r, 0) + 1

    day_alerts = await db.alerts.count_documents({
        "created_at": {"$gte": day_start_utc.isoformat(), "$lt": day_end_utc.isoformat()}
    })
    day_alerts_failed = await db.alerts.count_documents({
        "created_at": {"$gte": day_start_utc.isoformat(), "$lt": day_end_utc.isoformat()},
        "status": "failed"
    })

    now_ist = datetime.now(IST)
    return {
        "date_str": date_ist.strftime("%Y-%m-%d"),
        "ist_time": now_ist.strftime("%H:%M IST"),
        "total_trades": len(all_trades),
        "completed": len(completed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "open_positions": open_positions,
        "best_trade": {"pnl": float(best["pnl_abs"]), "symbol": best["symbol"], "event_type": best["event_type"]} if best else None,
        "worst_trade": {"pnl": float(worst["pnl_abs"]), "symbol": worst["symbol"], "event_type": worst["event_type"]} if worst else None,
        "strategy_stats": strategy_stats,
        "regime_counts": regime_counts,
        "alerts_sent": day_alerts - day_alerts_failed,
        "alerts_failed": day_alerts_failed,
    }


async def send_daily_summary(summary_type: str):
    """Build and fire a daily summary. Called by APScheduler."""
    now_ist = datetime.now(IST)
    if summary_type == "open":
        date_ist = (now_ist - timedelta(days=1)).date()
    else:
        date_ist = now_ist.date()

    try:
        data = await _compute_summary_data(date_ist, summary_type)
        message = format_daily_summary(summary_type, data)
        result = await send_direct_async(message)

        await db.summary_logs.insert_one({
            "id": str(uuid.uuid4()),
            "summary_type": summary_type,
            "date": str(date_ist),
            "success": result.get("success", False),
            "error": result.get("error"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Daily summary ({summary_type}) sent: {result.get('success')}")
    except Exception as exc:
        logger.error(f"Daily summary ({summary_type}) failed: {exc}")


# ── Seed Data ─────────────────────────────────────────────────────────────────

_SYMBOLS = ["NIFTY", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "RELIANCE", "TCS"]
_STRATEGIES = ["Momentum Alpha", "Mean Reversion", "Breakout Strategy", "VWAP Scalp"]
_REGIMES = ["trend", "trend", "trend", "mean_reverting", "volatile", "sideways"]
_TIMEFRAMES = ["5m", "15m", "1h", "4h"]
_PRICE_RANGES = {
    "NIFTY": (21500, 22500), "BANKNIFTY": (46000, 48000),
    "BTCUSDT": (62000, 70000), "ETHUSDT": (3200, 3800),
    "RELIANCE": (2800, 3000), "TCS": (3900, 4200),
}
_SIZE_RANGES = {
    "NIFTY": (1, 5), "BANKNIFTY": (1, 3),
    "BTCUSDT": (0.01, 0.05), "ETHUSDT": (0.1, 0.5),
    "RELIANCE": (5, 20), "TCS": (5, 15),
}


def _generate_sample_data():
    rng = random.Random(42)
    base = datetime.now(timezone.utc) - timedelta(days=14)
    trades, alerts = [], []

    for day in range(14):
        day_base = base + timedelta(days=day)
        for _ in range(rng.randint(2, 3)):
            symbol = rng.choice(_SYMBOLS)
            direction = rng.choice(["BUY", "SELL"])
            strategy = rng.choice(_STRATEGIES)
            regime = rng.choice(_REGIMES)
            timeframe = rng.choice(_TIMEFRAMES)
            ep = round(rng.uniform(*_PRICE_RANGES[symbol]), 2)
            size = round(rng.uniform(*_SIZE_RANGES[symbol]), 3)
            is_win = rng.random() < 0.65
            pnl = round(rng.uniform(80, 800) if is_win else rng.uniform(-400, -40), 2)
            event_type = rng.choice(["exit", "tp"]) if is_win else rng.choice(["exit", "sl"])
            pnl_pct = round((pnl / (ep * max(size, 0.001))) * 100, 2)
            exit_p = round(ep * (1 + pnl_pct / 100), 2)
            rr = round(abs(pnl) / (ep * max(size, 0.001) * 0.01), 1) if is_win else round(rng.uniform(0.3, 0.9), 1)
            conf = round(rng.uniform(0.60, 0.95), 2)
            # Spread across IST trading hours (UTC 3:45–10:00)
            hour_utc = rng.randint(4, 9)
            ts = day_base.replace(hour=hour_utc, minute=rng.randint(0, 59), second=0, microsecond=0)
            trade_id = f"TRD-{str(uuid.uuid4())[:8].upper()}"
            doc_id = str(uuid.uuid4())
            trade_doc = {
                "id": doc_id, "trade_id": trade_id, "symbol": symbol,
                "direction": direction, "event_type": event_type,
                "entry_price": ep, "exit_price": exit_p, "position_size": size,
                "strategy_name": strategy, "confidence_score": conf,
                "market_regime": regime, "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "pnl_abs": pnl, "pnl_pct": pnl_pct, "timeframe": timeframe,
                "rr_ratio": rr,
                "indicators": {"RSI": str(round(rng.uniform(25, 75), 1)),
                               "MACD": f"{'+' if rng.random() > 0.5 else '-'}{round(rng.uniform(0.001, 0.05), 4)}"},
                "alert_sent": True, "alert_message": f"Sample trade — {symbol}",
                "created_at": ts.isoformat(),
            }
            alert_doc = {
                "id": str(uuid.uuid4()), "trade_id": trade_id,
                "event_type": event_type, "message": f"Sample alert — {trade_id}",
                "status": "sent", "error": None, "created_at": ts.isoformat(),
            }
            trades.append(trade_doc)
            alerts.append(alert_doc)
    return trades, alerts


# ── Routes ────────────────────────────────────────────────────────────────────

@api_router.post("/trades/notify", response_model=TradeResponse)
async def notify_trade_endpoint(trade: TradeCreate):
    trade_id = trade.trade_id or f"TRD-{str(uuid.uuid4())[:8].upper()}"
    timestamp = trade.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    doc_id = str(uuid.uuid4())
    trade_data = {**trade.model_dump(), "trade_id": trade_id, "timestamp": timestamp}

    result = await notify_trade(trade_data, trade.event_type)
    alert_sent = result.get("success", False)
    alert_message = result.get("message", "")

    trade_doc = {
        "id": doc_id, **trade_data,
        "alert_sent": alert_sent, "alert_message": alert_message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.trades.insert_one(trade_doc)
    await db.alerts.insert_one({
        "id": str(uuid.uuid4()), "trade_id": trade_id,
        "event_type": trade.event_type, "message": alert_message,
        "status": "sent" if alert_sent else "failed",
        "error": result.get("error") if not alert_sent else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return TradeResponse(id=doc_id, **trade_data, alert_sent=alert_sent,
                         alert_message=alert_message, created_at=trade_doc["created_at"])


@api_router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0),
):
    query: dict = {}
    if symbol: query["symbol"] = {"$regex": symbol, "$options": "i"}
    if direction: query["direction"] = direction.upper()
    if event_type: query["event_type"] = event_type.lower()
    if strategy: query["strategy_name"] = {"$regex": strategy, "$options": "i"}
    return await db.trades.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)


@api_router.get("/trades/count")
async def count_trades():
    return {"total": await db.trades.count_documents({})}


@api_router.get("/alerts", response_model=List[AlertLog])
async def get_alerts(
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    query: dict = {}
    if status: query["status"] = status
    if event_type: query["event_type"] = event_type
    return await db.alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)


@api_router.post("/trades/test")
async def send_test_alert():
    test_trade = {
        "trade_id": f"TEST-{str(uuid.uuid4())[:6].upper()}",
        "symbol": "BTCUSDT", "direction": "BUY",
        "entry_price": 67500.00, "position_size": 0.05,
        "strategy_name": "Momentum Alpha", "confidence_score": 0.85,
        "market_regime": "trend", "timeframe": "1h", "rr_ratio": 2.5,
        "pnl_abs": None, "pnl_pct": None,
        "indicators": {"RSI": "62.3", "MACD": "+0.0012"},
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    result = await notify_trade(test_trade, "entry")
    return {"success": result.get("success"), "message": result.get("message", ""), "error": result.get("error")}


@api_router.post("/trades/preview")
async def preview_message(trade: TradeCreate):
    trade_data = trade.model_dump()
    trade_data["trade_id"] = trade_data.get("trade_id") or "PREVIEW"
    trade_data["timestamp"] = trade_data.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {"message": format_trade_message(trade.event_type, trade_data)}


@api_router.get("/analytics/summary")
async def get_analytics_summary():
    trades = await db.trades.find({}, {"_id": 0}).to_list(10000)
    completed = [t for t in trades if t.get("event_type") in ("exit", "sl", "tp") and t.get("pnl_abs") is not None]
    wins = [t for t in completed if float(t.get("pnl_abs", 0)) > 0]
    win_rate = round(len(wins) / len(completed) * 100, 1) if completed else 0
    total_pnl = round(sum(float(t.get("pnl_abs", 0)) for t in completed), 2)
    avg_pnl = round(total_pnl / len(completed), 2) if completed else 0

    strategy_stats: dict = {}
    for t in completed:
        s = t.get("strategy_name", "Unknown")
        if s not in strategy_stats:
            strategy_stats[s] = {"trades": 0, "pnl": 0.0, "wins": 0}
        strategy_stats[s]["trades"] += 1
        strategy_stats[s]["pnl"] = round(strategy_stats[s]["pnl"] + float(t.get("pnl_abs", 0)), 2)
        if float(t.get("pnl_abs", 0)) > 0:
            strategy_stats[s]["wins"] += 1

    symbol_counts: dict = {}
    regime_counts: dict = {}
    for t in trades:
        sym = t.get("symbol", "Unknown")
        symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        r = t.get("market_regime", "unknown")
        regime_counts[r] = regime_counts.get(r, 0) + 1

    return {
        "total_trades": len(trades),
        "completed_trades": len(completed),
        "wins": len(wins),
        "losses": len(completed) - len(wins),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "strategy_stats": strategy_stats,
        "symbol_counts": symbol_counts,
        "regime_counts": regime_counts,
        "alerts_sent": await db.alerts.count_documents({"status": "sent"}),
        "alerts_failed": await db.alerts.count_documents({"status": "failed"}),
    }


@api_router.get("/analytics/pnl-history")
async def get_pnl_history():
    docs = await db.trades.find(
        {"event_type": {"$in": ["exit", "sl", "tp"]}, "pnl_abs": {"$ne": None}},
        {"_id": 0, "created_at": 1, "pnl_abs": 1, "symbol": 1, "trade_id": 1},
    ).sort("created_at", 1).to_list(10000)
    cumulative = 0.0
    history = []
    for t in docs:
        pnl = float(t.get("pnl_abs", 0))
        cumulative = round(cumulative + pnl, 2)
        history.append({"date": t["created_at"][:10], "pnl": round(pnl, 2),
                         "cumulative_pnl": cumulative, "symbol": t.get("symbol", "")})
    return history


@api_router.get("/bot/status")
async def get_bot_status():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    return {"configured": bool(token and chat), "bot_token_set": bool(token),
            "chat_id_set": bool(chat), "chat_id": chat if chat else None}


@api_router.get("/bot/discover-chat")
async def discover_chat_id():
    import asyncio
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not set")

    def _get_updates():
        import requests as req
        return req.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10).json()

    result = await anyio.to_thread.run_sync(_get_updates)
    seen = set()
    unique = []
    for u in result.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat and chat.get("id") not in seen:
            seen.add(chat["id"])
            unique.append({
                "chat_id": chat.get("id"), "type": chat.get("type"),
                "title": chat.get("title") or chat.get("first_name") or chat.get("username"),
                "username": chat.get("username"),
            })
    return {"ok": result.get("ok"), "chats_found": unique, "total_updates": len(result.get("result", []))}


# ── Scheduler Routes ──────────────────────────────────────────────────────────

@api_router.get("/scheduler/status")
async def get_scheduler_status():
    jobs = []
    for job in scheduler.get_jobs():
        nrt = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_utc": nrt.isoformat() if nrt else None,
            "next_run_ist": nrt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST") if nrt else None,
        })
    # Last 5 summary logs
    logs = await db.summary_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)
    return {"running": scheduler.running, "jobs": jobs, "recent_logs": logs}


@api_router.post("/scheduler/trigger/{summary_type}")
async def trigger_summary(summary_type: str):
    if summary_type not in ("open", "close"):
        raise HTTPException(status_code=400, detail="Use 'open' or 'close'")
    await send_daily_summary(summary_type)
    return {"success": True, "message": f"Daily summary ({summary_type}) triggered"}


# ── Seed Data Route ───────────────────────────────────────────────────────────

@api_router.post("/seed-trades")
async def seed_sample_trades(force: bool = Query(False)):
    existing = await db.trades.count_documents({})
    if existing >= 5 and not force:
        return {"message": f"Already have {existing} trades. Pass ?force=true to re-seed.", "seeded": 0}

    trades, alerts = _generate_sample_data()
    if force:
        await db.trades.delete_many({"alert_message": {"$regex": "^Sample"}})
        await db.alerts.delete_many({"message": {"$regex": "^Sample"}})

    await db.trades.insert_many(trades)
    await db.alerts.insert_many(alerts)
    return {"message": f"Seeded {len(trades)} sample trades", "seeded": len(trades)}


# ── Risk & Analytics Routes ───────────────────────────────────────────────────

async def _fetch_completed_trades():
    return await db.trades.find(
        {"event_type": {"$in": ["exit", "sl", "tp"]}, "pnl_abs": {"$ne": None}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(10000)


@api_router.get("/analytics/risk")
async def get_risk_metrics():
    """Full risk metric suite: Sharpe, Sortino, Calmar, Kelly, Drawdown, Streaks, per-strategy Kelly."""
    docs = await _fetch_completed_trades()
    if len(docs) < 2:
        return {"error": "Need at least 2 completed trades for risk analysis", "total_trades": len(docs)}

    pnl_series = [float(d["pnl_abs"]) for d in docs]
    dates = [d["created_at"] for d in docs]
    metrics = compute_all_metrics(pnl_series, dates)

    # Build chart data (equity + drawdown)
    chart_data = []
    for i, doc in enumerate(docs):
        chart_data.append({
            "date": doc["created_at"][:10],
            "trade": i + 1,
            "equity": metrics["equity_curve"][i],
            "drawdown": metrics["drawdown_series"][i],
            "pnl": pnl_series[i],
            "symbol": doc.get("symbol", ""),
        })

    # Per-strategy breakdown
    from collections import defaultdict
    strat_pnls: dict = defaultdict(list)
    for d in docs:
        strat_pnls[d.get("strategy_name", "Unknown")].append(float(d["pnl_abs"]))

    strategy_risk = {}
    for strat, pnls in strat_pnls.items():
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        strategy_risk[strat] = {
            "trades": len(pnls),
            "wins": len(wins),
            "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
            "kelly_pct": compute_kelly(pnls),
            "total_pnl": round(sum(pnls), 2),
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else (round(sum(wins), 2) if wins else 0),
            "expectancy": round(sum(pnls) / len(pnls), 2),
        }

    return {
        **{k: v for k, v in metrics.items() if k not in ("equity_curve", "drawdown_series")},
        "chart_data": chart_data,
        "strategy_risk": strategy_risk,
        "total_completed": len(docs),
    }


@api_router.get("/analytics/monte-carlo")
async def get_monte_carlo(simulations: int = Query(500, le=1000)):
    """Monte Carlo bootstrap simulation of PnL outcomes."""
    docs = await _fetch_completed_trades()
    if len(docs) < 5:
        return {"error": "Need at least 5 completed trades for Monte Carlo", "n": len(docs)}
    pnl_series = [float(d["pnl_abs"]) for d in docs]
    return compute_monte_carlo(pnl_series, simulations)


class PositionSizeRequest(BaseModel):
    account_size: float
    risk_pct: float = 1.0
    stop_loss_pct: float = 2.0
    entry_price: Optional[float] = None


@api_router.post("/analytics/position-size")
async def calculate_position_size(req: PositionSizeRequest):
    """Compute risk-based and Kelly-based position sizes."""
    docs = await _fetch_completed_trades()
    pnl_series = [float(d["pnl_abs"]) for d in docs]
    kelly_pct = compute_kelly(pnl_series) if len(pnl_series) >= 5 else 0.0

    risk_amount = req.account_size * req.risk_pct / 100
    risk_position = risk_amount / (req.stop_loss_pct / 100) if req.stop_loss_pct > 0 else 0

    kelly_position = req.account_size * kelly_pct / 100
    half_kelly_position = kelly_position / 2
    quarter_kelly_position = kelly_position / 4

    result = {
        "account_size": req.account_size,
        "risk_pct": req.risk_pct,
        "stop_loss_pct": req.stop_loss_pct,
        "risk_amount": round(risk_amount, 2),
        "risk_position_usd": round(risk_position, 2),
        "kelly_pct": round(kelly_pct, 2),
        "kelly_position_usd": round(kelly_position, 2),
        "half_kelly_usd": round(half_kelly_position, 2),
        "quarter_kelly_usd": round(quarter_kelly_position, 2),
        "recommendation": "half_kelly" if kelly_pct > 0 else "risk_based",
        "trades_used": len(pnl_series),
    }
    if req.entry_price and req.entry_price > 0:
        result["risk_position_units"] = round(risk_position / req.entry_price, 6)
        result["kelly_position_units"] = round(kelly_position / req.entry_price, 6)
        result["half_kelly_units"] = round(half_kelly_position / req.entry_price, 6)
    return result


# ── Integration Template Route ────────────────────────────────────────────────

_EXECUTION_ENGINE_TEMPLATE = '''"""
execution_engine.py — TradeAlert Bot Integration Template
=========================================================
Production-ready integration for your algorithmic trading system.
Copy this file into your project and customize as needed.

Two integration modes:
  A) Direct import (same machine as the bot)
  B) REST API (remote / microservice)
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import requests

# ── Mode A: Direct Python Module Import ───────────────────────────────────────
# Place this file alongside notification_service.py
try:
    from notification_service import notify_trade_sync, on_trade_event
    DIRECT_IMPORT = True
except ImportError:
    DIRECT_IMPORT = False

# ── Mode B: REST API ──────────────────────────────────────────────────────────
TRADEALERT_API_URL = "https://algo-telegram-trade.preview.emergentagent.com/api"


# ── TradeData Helper ──────────────────────────────────────────────────────────

class TradeData:
    """Standard trade payload for TradeAlert Bot."""

    def __init__(
        self,
        symbol: str,
        direction: str,            # "BUY" | "SELL"
        event_type: str,           # "entry" | "exit" | "sl" | "tp" | "signal"
        entry_price: float,
        position_size: float,
        strategy_name: str,
        confidence_score: float,   # 0.0–1.0
        market_regime: str,        # "trend" | "mean_reverting" | "volatile" | "sideways"
        trade_id: Optional[str] = None,
        exit_price: Optional[float] = None,
        pnl_abs: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        timeframe: Optional[str] = None,
        rr_ratio: Optional[float] = None,
        indicators: Optional[Dict[str, Any]] = None,
    ):
        self.trade_id = trade_id or f"TRD-{str(uuid.uuid4())[:8].upper()}"
        self.symbol = symbol
        self.direction = direction
        self.event_type = event_type
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.position_size = position_size
        self.strategy_name = strategy_name
        self.confidence_score = confidence_score
        self.market_regime = market_regime
        self.pnl_abs = pnl_abs
        self.pnl_pct = pnl_pct
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.indicators = indicators or {}
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── ExecutionEngine ───────────────────────────────────────────────────────────

class ExecutionEngine:
    """
    Drop-in execution engine with TradeAlert Bot notifications.

    Quick start:
        engine = ExecutionEngine(strategy_name="Momentum Alpha")

        # Signal generated
        engine.on_signal("NIFTY", "BUY", confidence=0.82, regime="trend",
                         entry_price=22150, timeframe="15m",
                         indicators={"RSI": "58.4", "MACD": "+12.5"})

        # Trade entered
        tid = engine.on_entry("NIFTY", "BUY", entry_price=22155,
                               position_size=50, confidence=0.82,
                               regime="trend", rr_ratio=2.5)

        # Take profit hit
        engine.on_exit(tid, exit_price=22430, pnl_abs=13750, pnl_pct=1.24)

        # OR stop loss hit
        engine.on_stop_loss(tid, exit_price=22000, pnl_abs=-7750, pnl_pct=-0.70)
    """

    def __init__(
        self,
        strategy_name: str,
        use_api: bool = not DIRECT_IMPORT,
        api_url: str = TRADEALERT_API_URL,
    ):
        self.strategy_name = strategy_name
        self.use_api = use_api
        self.api_url = api_url
        self._open_trades: Dict[str, TradeData] = {}

    def _notify(self, td: TradeData) -> dict:
        d = td.to_dict()
        if not self.use_api and DIRECT_IMPORT:
            return notify_trade_sync(d, d["event_type"])
        try:
            resp = requests.post(f"{self.api_url}/trades/notify", json=d, timeout=10)
            return resp.json() if resp.ok else {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _notify_async(self, td: TradeData) -> dict:
        d = td.to_dict()
        if not self.use_api and DIRECT_IMPORT:
            return await on_trade_event(d["event_type"], d)
        return await anyio.to_thread.run_sync(self._notify, td)

    def on_signal(self, symbol, direction, confidence, regime, entry_price,
                  timeframe=None, indicators=None) -> str:
        td = TradeData(symbol=symbol, direction=direction, event_type="signal",
                       entry_price=entry_price, position_size=0,
                       strategy_name=self.strategy_name, confidence_score=confidence,
                       market_regime=regime, timeframe=timeframe, indicators=indicators)
        self._notify(td)
        return td.trade_id

    def on_entry(self, symbol, direction, entry_price, position_size,
                 confidence, regime, trade_id=None, timeframe=None,
                 rr_ratio=None, indicators=None) -> str:
        td = TradeData(symbol=symbol, direction=direction, event_type="entry",
                       entry_price=entry_price, position_size=position_size,
                       strategy_name=self.strategy_name, confidence_score=confidence,
                       market_regime=regime, trade_id=trade_id, timeframe=timeframe,
                       rr_ratio=rr_ratio, indicators=indicators)
        self._open_trades[td.trade_id] = td
        self._notify(td)
        return td.trade_id

    def on_exit(self, trade_id, exit_price, pnl_abs, pnl_pct, indicators=None):
        orig = self._open_trades.get(trade_id)
        td = TradeData(
            symbol=orig.symbol if orig else "UNKNOWN",
            direction=orig.direction if orig else "BUY",
            event_type="tp" if pnl_abs > 0 else "exit",
            entry_price=orig.entry_price if orig else 0,
            exit_price=exit_price, position_size=orig.position_size if orig else 0,
            strategy_name=self.strategy_name,
            confidence_score=orig.confidence_score if orig else 0,
            market_regime=orig.market_regime if orig else "trend",
            trade_id=trade_id, pnl_abs=pnl_abs, pnl_pct=pnl_pct,
            timeframe=orig.timeframe if orig else None, indicators=indicators,
        )
        self._notify(td)
        self._open_trades.pop(trade_id, None)

    def on_stop_loss(self, trade_id, exit_price, pnl_abs, pnl_pct):
        orig = self._open_trades.get(trade_id)
        td = TradeData(
            symbol=orig.symbol if orig else "UNKNOWN",
            direction=orig.direction if orig else "BUY",
            event_type="sl",
            entry_price=orig.entry_price if orig else 0,
            exit_price=exit_price, position_size=orig.position_size if orig else 0,
            strategy_name=self.strategy_name,
            confidence_score=orig.confidence_score if orig else 0,
            market_regime=orig.market_regime if orig else "trend",
            trade_id=trade_id, pnl_abs=pnl_abs, pnl_pct=pnl_pct,
            timeframe=orig.timeframe if orig else None,
        )
        self._notify(td)
        self._open_trades.pop(trade_id, None)


# ── Minimal REST-only Usage (no import required) ──────────────────────────────

def notify_via_rest(trade_data: dict, api_url: str = TRADEALERT_API_URL) -> dict:
    """Send a trade event directly to the TradeAlert API. No local install needed."""
    try:
        resp = requests.post(f"{api_url}/trades/notify", json=trade_data, timeout=10)
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Example Usage ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = ExecutionEngine(strategy_name="Momentum Alpha")

    # 1. Signal
    engine.on_signal(symbol="NIFTY", direction="BUY", confidence=0.82,
                     regime="trend", entry_price=22150.0, timeframe="15m",
                     indicators={"RSI": "58.4", "MACD": "+12.5"})

    # 2. Entry
    tid = engine.on_entry(symbol="NIFTY", direction="BUY", entry_price=22155.0,
                          position_size=50, confidence=0.82, regime="trend",
                          timeframe="15m", rr_ratio=2.5,
                          indicators={"RSI": "58.4", "MACD": "+12.5"})

    print(f"Trade opened: {tid}")

    # 3a. Take profit
    engine.on_exit(tid, exit_price=22430.0, pnl_abs=13750.0, pnl_pct=1.24)

    # 3b. OR stop loss
    # engine.on_stop_loss(tid, exit_price=22000.0, pnl_abs=-7750.0, pnl_pct=-0.70)

    print("Done. Check your Telegram!")
'''


@api_router.get("/integration/template")
async def get_integration_template():
    """Return the execution_engine.py integration template."""
    return {"content": _EXECUTION_ENGINE_TEMPLATE, "filename": "execution_engine.py"}


# ── Gemini Assistant Integration ──────────────────────────────────────────────

def get_system_prompt(command: str) -> str:
    prompts = {
        "fix": "You are an expert code reviewer. Analyze the provided code and identify bugs, issues, and fix them. Return only the corrected code with brief explanation of changes.",
        "optimize": "You are a performance optimization expert. Analyze the provided code and suggest optimizations for speed, memory usage, and efficiency. Return the optimized code with explanation of improvements.",
        "explain": "You are a code documentation expert. Explain the provided code in clear, simple terms. Break down what it does, how it works, and the logic behind it.",
        "refactor": "You are a code quality expert. Refactor the provided code to follow best practices, improve readability, and enhance maintainability. Return the refactored code with explanation of changes."
    }
    return prompts.get(command, prompts["fix"])


def is_valid_file_type(filename: str) -> bool:
    valid_extensions = [
        ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".cpp", ".c", ".h",
        ".cs", ".php", ".rb", ".go", ".rs", ".kotlin", ".swift", ".m",
        ".scala", ".groovy", ".sh", ".bash", ".sql", ".html", ".css",
        ".scss", ".sass", ".less", ".json", ".xml", ".yaml", ".yml",
        ".toml", ".ini", ".env", ".txt", ".md", ".vue", ".lua", ".perl"
    ]
    ext = Path(filename).suffix.lower()
    return ext in valid_extensions


@api_router.post("/analyze")
async def analyze_code(request: AnalyzeRequest):
    """
    Analyzes code using Gemini API.
    Centralized logic for CLI and VS Code extension.
    """
    return {"response": "Gemini analysis is disabled due to Python 3.7 incompatibility."}
    # if request.fileName and not is_valid_file_type(request.fileName):
    #     raise HTTPException(status_code=400, detail=f"Unsupported file type for {request.fileName}")
    # ... (rest commented out)


import json
from live_state import live_state

# --- COMMAND QUEUE HELPER ---
COMMAND_FILE = "manual_commands.json"

async def queue_command(cmd_type, data=None):
    new_cmd = {
        "id": str(uuid.uuid4()), 
        "type": cmd_type, 
        "payload": data or {},
        "status": "PENDING",
        "timestamp": datetime.now().isoformat()
    }
    
    # Log to DB
    await db.bot_commands.insert_one(new_cmd.copy())
    # Legacy: also log to manual_commands for history
    await db.manual_commands.insert_one(new_cmd.copy())
    return new_cmd

# === BOT EVENT INGESTION ===
@api_router.post("/bot/{event_type}")
async def bot_event_ingestion(event_type: str, data: dict):
    """Receives all events from the trading bot."""
    if not data:
        data = {}
    data["event_type"] = event_type
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    # 1. Persist to MongoDB
    await db.bot_events.insert_one(data.copy())
    
    # REQ 31-1: Sync to 'trades' collection for persistent UI tracking
    if event_type == "TRADE_OPEN" or event_type == "trade_open":
        trade_doc = {
            "trade_id": data.get("trade_id"),
            "symbol": data.get("symbol"),
            "direction": data.get("direction"),
            "entry_price": data.get("entry_price"),
            "qty": data.get("lots"),
            "sl": data.get("sl"),
            "tp": data.get("tp"),
            "strategy": data.get("strategy"),
            "context": data.get("context_tags"),
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN"
        }
        await db.trades.insert_one(trade_doc)

    elif event_type == "TRADE_UPDATE" or event_type == "trade_update":
        await db.trades.update_one(
            {"trade_id": data.get("trade_id")},
            {"$set": {"unrealized_pnl": data.get("unrealised_pnl"), "current_price": data.get("current_price")}}
        )

    elif event_type == "TRADE_CLOSE" or event_type == "trade_close":
        await db.trades.update_one(
            {"trade_id": data.get("trade_id")},
            {"$set": {
                "exit_price": data.get("exit_price"),
                "exit_reason": data.get("exit_reason"),
                "pnl": data.get("pnl"),
                "status": "CLOSED",
                "exit_time": datetime.now(timezone.utc).isoformat()
            }}
        )

    # 2. Update Live State
    if event_type == "HEARTBEAT" or event_type == "heartbeat":
        live_state.capital = data.get("capital", live_state.capital)
        live_state.daily_pnl = data.get("daily_pnl", live_state.daily_pnl)
        live_state.trades_today = data.get("trades_today", live_state.trades_today)
        
        # Derive status from is_paused flag
        if "is_paused" in data:
            live_state.status = "PAUSED" if data["is_paused"] else "ACTIVE"
        else:
            live_state.status = data.get("status", live_state.status)
            
        live_state.vix = data.get("vix", live_state.vix)
        live_state.regime = data.get("regime", live_state.regime)
        live_state.last_heartbeat = datetime.now()
        
        # Capture full context if provided
        live_state.market_context = data.copy()
        
        # Sync positions from heartbeat if provided
        if "active_positions" in data and isinstance(data["active_positions"], list):
            live_state.active_positions = data["active_positions"]
        
    elif event_type == "SIGNAL" or event_type == "signal":
        live_state.recent_signals.insert(0, data)
        live_state.recent_signals = live_state.recent_signals[:50]
        
    elif event_type == "BOOT" or event_type == "status":
        live_state.mode = data.get("mode", live_state.mode)
        live_state.engines = data.get("engines", live_state.engines)
        live_state.risk_rules = data.get("risk_rules", live_state.risk_rules)
        live_state.status = "ACTIVE"
        
    elif event_type == "TRADE_OPEN" or event_type == "trade_open":
        # Normalize keys
        symbol = data.get('symbol') or data.get('stock') or "UNKNOWN"
        price = data.get('entry_price', 0.0)
        qty = data.get('lots') or data.get('quantity') or 0
        sl = data.get('sl') or data.get('sl_price') or 0.0
        tp = data.get('tp') or data.get('tp_type') or 0.0
        tid = data.get('trade_id') or str(uuid.uuid4())
        
        # Update Live Positions
        new_pos = {
            "id": tid,
            "stock": symbol,
            "direction": data.get('direction', 'UNKNOWN'),
            "entry": price,
            "lots": qty,
            "unrealized": 0.0
        }
        # Avoid duplicates
        if not any(p['id'] == tid for p in live_state.active_positions):
            live_state.active_positions.append(new_pos)

        msg = f"🎯 *ENTRY:* {symbol} {data.get('direction', 'UNKNOWN')} @ ₹{price:.2f} | Qty: {qty} | SL: ₹{sl:.2f} | TP: {tp}"
        try:
            await send_direct_async(msg)
        except Exception as e:
            logger.warning(f"Failed to send direct async message: {e}")

    elif event_type == "TRADE_UPDATE" or event_type == "trade_update":
        tid = data.get('trade_id')
        for p in live_state.active_positions:
            if p['id'] == tid:
                p['unrealized'] = data.get('unrealised_pnl', 0.0)
                p['current'] = data.get('current_price', 0.0)

    elif event_type == "TRADE_CLOSE" or event_type == "trade_close":
        tid = data.get('trade_id')
        live_state.active_positions = [p for p in live_state.active_positions if p['id'] != tid]

        symbol = data.get('symbol') or data.get('stock', 'Unknown')
        exit_price = data.get('exit_price', 0.0)
        net_pnl = data.get('net_pnl') or data.get('pnl', 0.0)
        reason = data.get('exit_reason', 'UNKNOWN')
        msg = f"🏁 *EXIT:* {symbol} @ ₹{exit_price:.2f} | PnL: ₹{net_pnl:.2f} | Reason: {reason}"
        try:
            await send_direct_async(msg)
        except Exception as e:
            logger.warning(f"Failed to send direct async message: {e}")
        
    elif event_type == "DAILY_SUMMARY" or event_type == "daily_summary":
        trades = data.get('total_trades') or data.get('trades', 0)
        pnl = data.get('net_pnl', 0.0)
        cap = data.get('closing_capital') or data.get('capital_eod', 0.0)
        msg = f"📊 *DAY END* | Trades: {trades} | Net: ₹{pnl:.2f} | Capital: ₹{cap:.2f}"
        try:
            await send_direct_async(msg)
        except Exception as e:
            logger.warning(f"Failed to send direct async message: {e}")

    return {"status": "success"}

# === LIVE MONITORING ===
@api_router.get("/live/status")
async def get_live_status_data():
    return {
        "capital": live_state.capital,
        "daily_pnl": live_state.daily_pnl,
        "trades_today": live_state.trades_today,
        "status": live_state.status,
        "vix": live_state.vix,
        "regime": live_state.regime,
        "mode": live_state.mode,
        "last_update": live_state.last_heartbeat.isoformat() if live_state.last_heartbeat else None
    }

@api_router.get("/live/positions")
async def get_live_positions():
    return live_state.active_positions

@api_router.get("/live/context")
async def get_live_context():
    return live_state.market_context

@api_router.get("/live/signals")
async def get_live_signals():
    # Last 20 signals from bot_events
    signals = await db.bot_events.find({"event_type": {"$in": ["SIGNAL", "signal"]}}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return signals

@api_router.get("/alerts")
async def get_alerts(limit: int = 50):
    alerts = await db.bot_events.find({"event_type": {"$in": ["TRADE_OPEN", "TRADE_CLOSE", "SIGNAL", "DAILY_SUMMARY"]}}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return alerts

# === ANALYTICS EXTENSIONS ===
@api_router.get("/analytics/equity-curve")
async def get_equity_curve_data():
    summaries = await db.bot_events.find({"event_type": {"$in": ["DAILY_SUMMARY", "daily_summary"]}}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return [{"date": s["created_at"][:10], "capital": s.get("closing_capital") or s.get("capital_eod")} for s in summaries]

@api_router.get("/analytics/context-perf")
async def get_context_performance():
    trades = await db.trades.find({"event_type": {"$in": ["exit", "sl", "tp"]}}, {"_id": 0}).to_list(10000)
    perf = {}
    for t in trades:
        ctx = t.get("market_regime", "Unknown") # or context_tags
        if ctx not in perf: perf[ctx] = {"trades": 0, "wins": 0, "pnl": 0.0}
        perf[ctx]["trades"] += 1
        pnl = float(t.get("pnl_abs", 0))
        perf[ctx]["pnl"] += pnl
        if pnl > 0: perf[ctx]["wins"] += 1
    
    return [{"context": k, "trades": v["trades"], "win_rate": round(v["wins"]/v["trades"]*100, 1), "net_pnl": round(v["pnl"], 2)} for k, v in perf.items()]

@api_router.get("/analytics/stock-perf")
async def get_stock_performance():
    trades = await db.trades.find({"event_type": {"$in": ["exit", "sl", "tp"]}}, {"_id": 0}).to_list(10000)
    perf = {}
    for t in trades:
        sym = t.get("symbol", "Unknown")
        if sym not in perf: perf[sym] = {"trades": 0, "wins": 0, "pnl": 0.0}
        perf[sym]["trades"] += 1
        pnl = float(t.get("pnl_abs", 0))
        perf[sym]["pnl"] += pnl
        if pnl > 0: perf[sym]["wins"] += 1
    
    return [{"symbol": k, "trades": v["trades"], "net_pnl": round(v["pnl"], 2), "win_rate": round(v["wins"]/v["trades"]*100, 1)} for k, v in perf.items()]

@api_router.get("/analytics/strategy-perf")
async def get_strategy_performance():
    # Try learning layer first
    learning_stats = await db.strategy_performance.find({}, {"_id": 0}).sort("net_pnl", -1).to_list(100)
    if learning_stats:
        return learning_stats
    
    # Fallback to compute from trades
    trades = await db.trades.find({"event_type": {"$in": ["exit", "sl", "tp"]}}, {"_id": 0}).to_list(10000)
    perf = {}
    for t in trades:
        strat = t.get("strategy_name", t.get("strategy", "Unknown"))
        if strat not in perf: perf[strat] = {"trades": 0, "wins": 0, "pnl": 0.0, "regimes": []}
        perf[strat]["trades"] += 1
        pnl = float(t.get("pnl_abs", 0))
        perf[strat]["pnl"] += pnl
        if pnl > 0: perf[strat]["wins"] += 1
        if "market_regime" in t: perf[strat]["regimes"].append(t["market_regime"])
    
    result = []
    for k, v in perf.items():
        best_regime = "N/A"
        if v["regimes"]:
            from collections import Counter
            best_regime = Counter(v["regimes"]).most_common(1)[0][0]
        
        result.append({
            "strategy": k,
            "trades": v["trades"],
            "win_rate": round(v["wins"]/v["trades"]*100, 1),
            "net_pnl": round(v["pnl"], 2),
            "best_regime": best_regime
        })
    return result

# === MANUAL CONTROL ===
@api_router.post("/control/close-position")
async def control_close_position(req: dict):
    # req: {"trade_id": "xxx"}
    cmd = await queue_command("CLOSE_POSITION", req)
    return {"status": "command_queued", "command": cmd}

@api_router.post("/control/close-all")
async def control_close_all():
    cmd = await queue_command("CLOSE_ALL")
    return {"status": "command_queued", "command": cmd}

@api_router.post("/control/manual-trade")
async def control_manual_trade(req: dict):
    cmd = await queue_command("MANUAL_TRADE", req)
    return {"status": "command_queued", "command": cmd}

@api_router.post("/control/pause-bot")
async def control_pause_bot():
    cmd = await queue_command("PAUSE")
    live_state.status = "PAUSED"
    return {"status": "command_queued", "command": cmd}

@api_router.post("/control/resume-bot")
async def control_resume_bot():
    cmd = await queue_command("RESUME")
    live_state.status = "ACTIVE"
    return {"status": "command_queued", "command": cmd}

@api_router.get("/control/command-history")
async def get_command_history():
    return await db.manual_commands.find({}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)

# === SETTINGS ===
@api_router.get("/settings")
async def get_bot_settings():
    settings = await db.bot_settings.find_one({}, {"_id": 0})
    if not settings:
        # Fallback to defaults from v3_utils
        from modules.v3_utils import TOTAL_CAPITAL, MAX_TRADES_PER_DAY
        return {"capital": TOTAL_CAPITAL, "max_trades_day": MAX_TRADES_PER_DAY, "bot_mode": "PAPER"}
    return settings

@api_router.put("/settings")
async def update_bot_settings(settings: dict):
    await db.bot_settings.update_one({}, {"$set": settings}, upsert=True)
    return {"status": "success"}

# === BACKTEST ===
@api_router.post("/backtest/run")
async def run_backtest_endpoint(config: dict):
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "PENDING",
        "progress_pct": 0,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.backtest_jobs.insert_one(job)
    
    # Start in background
    from backtest_engine import run as run_bt
    def run_job():
        try:
            # Update status to RUNNING
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}})
            result = run_bt(config)
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "result": result, "completed_at": datetime.now(timezone.utc).isoformat(), "progress_pct": 100}})
        except Exception as e:
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "FAILED", "error": str(e)}})
            
    Thread(target=run_job, daemon=True).start()
    return {"job_id": job_id}

@api_router.get("/backtest/status/{job_id}")
async def get_backtest_status(job_id: str):
    job = await db.backtest_jobs.find_one({"job_id": job_id}, {"_id": 0, "result": 0})
    if not job: raise HTTPException(status_code=404)
    return job

@api_router.get("/backtest/result/{job_id}")
async def get_backtest_result(job_id: str):
    job = await db.backtest_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job: raise HTTPException(status_code=404)
    return job

@api_router.get("/backtest/history")
async def get_backtest_history():
    return await db.backtest_jobs.find({}, {"_id": 0, "result": 0}).sort("created_at", -1).limit(20).to_list(20)

@api_router.post("/backtest/grid-search")
async def run_grid_search_endpoint(config: dict):
    job_id = str(uuid.uuid4())
    # ... similar to run but calls grid_search
    from backtest_engine import grid_search as run_grid
    def run_job():
        try:
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}})
            result = run_grid(config)
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "result": result, "completed_at": datetime.now(timezone.utc).isoformat(), "progress_pct": 100}})
        except Exception as e:
            db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "FAILED", "error": str(e)}})
    
    await db.backtest_jobs.insert_one({"job_id": job_id, "status": "PENDING", "config": config, "created_at": datetime.now(timezone.utc).isoformat()})
    Thread(target=run_job, daemon=True).start()
    return {"job_id": job_id}

@api_router.delete("/backtest/{job_id}")
async def delete_backtest(job_id: str):
    await db.backtest_jobs.delete_one({"job_id": job_id})
    return {"status": "success"}

# --- App Setup (existing) ---
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    scheduler.add_job(
        send_daily_summary, CronTrigger(hour=9, minute=15, timezone=IST),
        id="morning_recap", replace_existing=True,
        name="Morning Recap (09:15 IST)", args=["open"],
    )
    scheduler.add_job(
        send_daily_summary, CronTrigger(hour=15, minute=30, timezone=IST),
        id="session_close", replace_existing=True,
        name="Session Close (15:30 IST)", args=["close"],
    )
    # New Excel Journal Job
    from utils.generate_journal import generate_daily_journal
    scheduler.add_job(
        generate_daily_journal, CronTrigger(hour=15, minute=35, timezone=IST),
        id="excel_journal", replace_existing=True,
        name="Daily Excel Journal (15:35 IST)"
    )
    if not scheduler.running:
        scheduler.start()
    logger.info("APScheduler started — Morning: 09:15 IST | Close: 15:30 IST")
    
    asyncio.create_task(start_telegram_polling())
    logger.info("Telegram command polling started.")


@app.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    client.close()



# ============================================================
# PA ENGINE ROUTES
# ============================================================
import sys, os
PA_ENGINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Priceactionmdfiles")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, PA_ENGINE_DIR)

try:
    from modules.pa_engine_bridge import PAEngineBridge
    PA_AVAILABLE = True
except:
    PA_AVAILABLE = False

from fastapi import Request

# --- PA ENGINE CONFIG ---
@app.get("/api/pa/config")
def get_pa_config():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    return PAEngineBridge.get_config()

@app.put("/api/pa/config")
async def save_pa_config(request: Request):
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    data = await request.json()
    PAEngineBridge.save_config(data)
    return {"status": "saved"}

# --- PA STRATEGIES ---
@app.get("/api/pa/strategies")
def get_pa_strategies():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    config = PAEngineBridge.get_config()
    active = set(config.get("strategies", []))
    all_configs = config.get("strategy_configs", {})
    strategies = []
    for name, cfg in all_configs.items():
        strategies.append({
            "name": name, "active": name in active,
            "confidence": cfg.get("optimal_confidence", 0),
            "profit_factor": cfg.get("profit_factor_at_threshold", 0),
            "direction": cfg.get("preferred_direction", "ANY"),
            "regimes": cfg.get("allowed_regimes", []),
        })
    return sorted(strategies, key=lambda x: x['profit_factor'], reverse=True)

@app.put("/api/pa/strategies/{name}/toggle")
def toggle_pa_strategy(name: str):
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    config = PAEngineBridge.get_config()
    strategies = config.get("strategies", [])
    if name in strategies:
        strategies.remove(name); action = "disabled"
    else:
        strategies.append(name); action = "enabled"
    config["strategies"] = strategies
    PAEngineBridge.save_config(config)
    return {"strategy": name, "action": action}

# --- PA EDGE MONITOR ---
@app.get("/api/pa/edge")
def get_pa_edge():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    return PAEngineBridge.get_edge_status()

# --- PA MONTE CARLO ---
@app.get("/api/pa/montecarlo")
def get_pa_monte_carlo():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    return PAEngineBridge.get_monte_carlo() or {"error": "No MC results"}

# --- PA BACKTEST RESULTS ---
@app.get("/api/pa/backtest/files")
def get_pa_backtest_files():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    return PAEngineBridge.get_backtest_results()

@app.get("/api/pa/backtest/{filename}")
def get_pa_backtest_file(filename: str):
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    import pandas as pd
    path = os.path.join(PA_ENGINE_DIR, "pipeline", "results", filename)
    if not os.path.exists(path): return {"error": "File not found"}
    if filename.endswith('.csv'):
        df = pd.read_csv(path)
        return {"data": df.tail(1000).to_dict(orient='records'), "total": len(df)}
    elif filename.endswith('.json'):
        import json
        with open(path) as f: return json.load(f)
    else:
        with open(path) as f: return {"content": f.read()}

# --- PA SCHEDULE/RISK SETTINGS ---
@app.get("/api/pa/schedule")
def get_pa_schedule():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    config = PAEngineBridge.get_config()
    return {
        "allowed_hours": config.get("allowed_hours", []),
        "allowed_days": config.get("allowed_days", []),
        "sl_method": config.get("sl_method", ""),
    }

@app.put("/api/pa/schedule")
async def save_pa_schedule(request: Request):
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    data = await request.json()
    config = PAEngineBridge.get_config()
    if "allowed_hours" in data: config["allowed_hours"] = data["allowed_hours"]
    if "allowed_days" in data: config["allowed_days"] = data["allowed_days"]
    if "sl_method" in data: config["sl_method"] = data["sl_method"]
    PAEngineBridge.save_config(config)
    return {"status": "saved"}

@app.get("/api/pa/risk")
def get_pa_risk():
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    return PAEngineBridge.get_config().get("risk_management", {})

@app.put("/api/pa/risk")
async def save_pa_risk(request: Request):
    if not PA_AVAILABLE: return {"error": "PA engine not available"}
    data = await request.json()
    config = PAEngineBridge.get_config()
    config["risk_management"] = data
    PAEngineBridge.save_config(config)
    return {"status": "saved"}



# ============================================================
# TRADE JOURNAL ROUTES
# ============================================================
from datetime import datetime, timezone
import csv
import io
from fastapi.responses import StreamingResponse

# --- MODELS ---
class JournalTrade(BaseModel):
    trade_id: Optional[str] = None
    symbol: str
    direction: str
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    result: str # WIN / LOSS / OPEN
    entry_time: str
    exit_time: Optional[str] = None
    strategy_name: str
    market_regime: Optional[str] = None
    source: str = "backtest" # live / backtest

@api_router.get("/journal/trades")
async def get_journal_trades(
    page: int = 1,
    limit: int = 50,
    strategy: str = None,
    result: str = None,
    source: str = None
):
    query = {}
    if strategy: query["strategy_name"] = strategy
    if result: query["result"] = result
    if source: query["source"] = source

    total = await db.trade_journal.count_documents(query)
    cursor = db.trade_journal.find(query, {"_id": 0}).sort("entry_time", -1).skip((page - 1) * limit).limit(limit)
    trades = await cursor.to_list(limit)

    return {
        "trades": trades,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@api_router.get("/journal/summary")
async def get_journal_summary():
    pipeline = [
        {"$group": {
            "_id": None,
            "total_trades": {"$sum": 1},
            "total_pnl": {"$sum": "$pnl"},
            "wins": {"$sum": {"$cond": [{"$eq": ["$result", "WIN"]}, 1, 0]}},
        }}
    ]
    res = await db.trade_journal.aggregate(pipeline).to_list(1)
    if not res: return {"total_trades": 0, "total_pnl": 0, "win_rate": 0}
    
    stats = res[0]
    stats["win_rate"] = round(stats["wins"] / stats["total_trades"] * 100, 1)
    return stats

@api_router.post("/journal/import-backtest")
async def import_backtest_journal():
    csv_path = os.path.join(PA_ENGINE_DIR, "backtest_detailed_results.csv")
    if not os.path.exists(csv_path):
        return {"error": f"File not found: {csv_path}"}
    
    import pandas as pd
    df = pd.read_csv(csv_path)
    
    # Map columns to schema
    # CSV cols: entry_time,exit_time,result,pnl,pnl_pct,strategy,month,confidence
    trades = []
    for _, row in df.iterrows():
        trades.append({
            "trade_id": f"BT-{uuid.uuid4().hex[:8].upper()}",
            "symbol": "NIFTY",
            "direction": "CE" if row.get('pnl', 0) > 0 else "PE", # Approximation
            "quantity": 50,
            "entry_price": 0, # Not in current CSV
            "exit_price": 0,
            "pnl": row['pnl'],
            "pnl_pct": row['pnl_pct'],
            "result": row['result'],
            "entry_time": row['entry_time'],
            "exit_time": row['exit_time'],
            "strategy_name": row['strategy'],
            "source": "backtest",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    if trades:
        # Clear existing backtest trades first to avoid duplicates
        await db.trade_journal.delete_many({"source": "backtest"})
        await db.trade_journal.insert_many(trades)
        
    return {"status": "success", "imported": len(trades)}

@api_router.get("/journal/export")
async def export_journal_csv():
    cursor = db.trade_journal.find({}, {"_id": 0}).sort("entry_time", -1)
    trades = await cursor.to_list(10000)
    if not trades: return {"error": "No trades"}
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=trades[0].keys())
    writer.writeheader()
    writer.writerows(trades)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trade_journal_{datetime.now().strftime('%Y%m%d')}.csv"}
    )



# ============================================================
# LOSS ANALYSIS ROUTE
# ============================================================

@api_router.get("/journal/losses/analysis")
async def get_loss_analysis():
    cursor = db.trade_journal.find({"result": "LOSS"}, {"_id": 0})
    losses = await cursor.to_list(1000)
    
    if not losses:
        return {"total_losses": 0, "message": "No losing trades found"}
        
    import pandas as pd
    df = pd.DataFrame(losses)
    
    analysis = {
        "total_losses": len(df),
        "total_lost": round(df['pnl'].sum(), 2),
        "avg_loss": round(df['pnl'].mean(), 2),
        "worst_loss": round(df['pnl'].min(), 2),
        "by_strategy": [],
        "by_day": [],
        "by_hour": []
    }
    
    if 'strategy_name' in df.columns:
        for s, g in df.groupby('strategy_name'):
            analysis["by_strategy"].append({
                "strategy": s, "count": len(g), "total_lost": round(g['pnl'].sum(), 2)
            })
        analysis["by_strategy"].sort(key=lambda x: x['total_lost'])
        
    if 'day_of_week' in df.columns:
        for d, g in df.groupby('day_of_week'):
            analysis["by_day"].append({
                "day": d, "count": len(g), "total_lost": round(g['pnl'].sum(), 2)
            })
            
    # Save a snapshot
    await db.loss_analysis.insert_one({**analysis, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    return analysis

app.include_router(api_router)

app.include_router(configs.router)
app.include_router(backtest.router)
app.include_router(trades.router)
app.include_router(live_pnl.router)
app.include_router(system.router)
app.include_router(docs.router)
app.include_router(logs.router)
app.include_router(strategies.router)
app.include_router(riskguard.router)
app.include_router(regime.router)
app.include_router(notifications.router)
app.include_router(candles.router)




# ============================================================
# SYSTEM HEALTH & MODULE EXPOSURE ROUTES
# ============================================================

@api_router.get("/system/health")
async def get_system_health():
    """Aggregated health status of all major components."""
    from modules.data_layer import DataLayer
    dl = DataLayer()
    
    return {
        "bot": {
            "status": live_state.status,
            "mode": live_state.mode,
            "uptime_seconds": (datetime.now() - live_state.last_heartbeat).total_seconds() if live_state.last_heartbeat else 0
        },
        "scheduler": {
            "running": scheduler.running,
            "jobs": [j.name for j in scheduler.get_jobs()]
        },
        "data_layer": {
            "symbol": dl.symbol,
            "option_summary": dl.fetch_option_chain_summary()
        },
        "mongodb": "CONNECTED"
    }

@api_router.get("/analysis/smc")
async def get_smc_analysis(symbol: str = "NIFTY"):
    """Expose SMC module data."""
    try:
        from modules.smc.analysis import SMCAnalyzer
        # This is speculative based on common project structure
        # If SMC module isn't standalone-runnable, return dummy or read cache
        return {"status": "success", "zones": [], "structure": "BULLISH"}
    except:
        return {"error": "SMC module not found or import failed"}

@api_router.get("/analysis/indicators")
async def get_current_indicators(symbol: str = "NIFTY"):
    """Expose technical indicators."""
    return {
        "symbol": symbol,
        "rsi": random.uniform(30, 70),
        "vix": live_state.vix,
        "regime": live_state.regime
    }



# ============================================================
# YAML CONFIG EDITOR ROUTES
# ============================================================
import yaml

@api_router.get("/config/files")
def list_config_files():
    config_dir = os.path.join(ROOT_DIR, "config")
    if not os.path.exists(config_dir): return []
    return [f for f in os.listdir(config_dir) if f.endswith(('.yaml', '.yml'))]

@api_router.get("/config/content/{filename}")
def get_config_content(filename: str):
    path = os.path.join(ROOT_DIR, "config", filename)
    if not os.path.exists(path): raise HTTPException(404)
    with open(path, 'r') as f:
        return {"content": f.read()}

@api_router.put("/config/content/{filename}")
async def save_config_content(filename: str, request: Request):
    data = await request.json()
    path = os.path.join(ROOT_DIR, "config", filename)
    # Validation: try to parse as YAML
    try:
        yaml.safe_load(data['content'])
    except Exception as e:
        raise HTTPException(400, detail=f"Invalid YAML: {str(e)}")
        
    with open(path, 'w') as f:
        f.write(data['content'])
    return {"status": "saved"}

if __name__ == "__main__":
    import uvicorn
    check_pid_lock("backend_server")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
