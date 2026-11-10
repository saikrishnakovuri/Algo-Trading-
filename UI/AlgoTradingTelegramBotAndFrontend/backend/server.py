from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import random
import uuid
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import google.generativeai as genai
from risk_calculator import (
    compute_all_metrics, compute_kelly, compute_monte_carlo,
    compute_equity_curve,
)
from notification_service import notify_trade

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

IST = pytz.timezone("Asia/Kolkata")

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

app = FastAPI(title="TradeAlert Bot API")
api_router = APIRouter(prefix="/api")

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

    result = await asyncio.to_thread(_get_updates)
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
        return await asyncio.to_thread(self._notify, td)

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
    if request.fileName and not is_valid_file_type(request.fileName):
        raise HTTPException(status_code=400, detail=f"Unsupported file type for {request.fileName}")

    try:
        system_prompt = get_system_prompt(request.command)
        
        full_prompt = f"{system_prompt}\n\n"
        if request.fileName:
            full_prompt += f"File: {request.fileName}\n\n"
        
        full_prompt += f"Code:\n```\n{request.code}\n```"
        
        if request.context:
            full_prompt += f"\n\nAdditional Context: {request.context}"

        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(full_prompt)
        
        if not response or not response.text:
            raise HTTPException(status_code=500, detail="Empty response from Gemini API")

        return {"response": response.text}

    except Exception as e:
        logger.error(f"Gemini API Error: {str(e)}")
        # Map some common errors to status codes
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a moment.")
        if "401" in str(e) or "UNAUTHENTICATED" in str(e):
            raise HTTPException(status_code=401, detail="Invalid API key or authentication error.")
        
        raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")


# ── App Setup ─────────────────────────────────────────────────────────────────

app.include_router(api_router)
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
    if not scheduler.running:
        scheduler.start()
    logger.info("APScheduler started — Morning: 09:15 IST | Close: 15:30 IST")


@app.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    client.close()
