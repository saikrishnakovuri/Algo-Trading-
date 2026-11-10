"""
Telegram Trade Alert Notification Service
==========================================
Pluggable, event-driven notification module for algorithmic trading systems.

Async usage (FastAPI / asyncio):
    from notification_service import notify_trade, on_trade_event
    await notify_trade(trade_data, "entry")
    await on_trade_event("entry", trade_data)

Sync usage (regular Python algo code):
    from notification_service import notify_trade_sync
    notify_trade_sync(trade_data, "entry")

Trade data dict keys:
    trade_id, symbol, direction, entry_price, exit_price,
    position_size, strategy_name, confidence_score, market_regime,
    timestamp, pnl_abs, pnl_pct, timeframe, rr_ratio, indicators
"""

import asyncio
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_URL: str = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

RATE_LIMIT_SECONDS: float = 3.0
_last_sent_time: float = 0.0
_sent_fingerprints: set = set()

EVENT_EMOJIS = {
    "entry": "🟢",
    "exit": "🔵",
    "sl": "🔴",
    "tp": "✅",
    "signal": "⚡",
}

DIRECTION_EMOJIS = {"BUY": "⬆️", "SELL": "⬇️"}

REGIME_LABELS = {
    "trend": "📈 Trending",
    "mean_reverting": "🔄 Mean-Reverting",
    "volatile": "⚡ Volatile",
    "sideways": "➡️ Sideways",
}

EVENT_NAMES = {
    "entry": "TRADE ENTRY",
    "exit": "TRADE EXIT",
    "sl": "STOP LOSS HIT",
    "tp": "TAKE PROFIT HIT",
    "signal": "SIGNAL GENERATED",
}


def _esc(text: str) -> str:
    """Escape Markdown-sensitive chars in user-supplied data."""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")


def _fingerprint(event_type: str, trade_id: str) -> str:
    return hashlib.md5(f"{trade_id}_{event_type}".encode()).hexdigest()


def format_trade_message(event_type: str, trade_data: dict) -> str:
    """Build a structured Telegram Markdown message for a trade event."""
    et = event_type.lower()
    event_emoji = EVENT_EMOJIS.get(et, "📊")
    event_name = EVENT_NAMES.get(et, event_type.upper())
    direction = str(trade_data.get("direction", "")).upper()
    dir_emoji = DIRECTION_EMOJIS.get(direction, "")
    regime = str(trade_data.get("market_regime", "")).lower()
    regime_label = REGIME_LABELS.get(regime, "📊 Unknown")
    symbol = _esc(trade_data.get("symbol", "UNKNOWN"))

    lines = [
        f"{event_emoji} *{event_name}* | `{symbol}`",
        "",
        f"*Strategy:* {_esc(trade_data.get('strategy_name', 'N/A'))}",
        f"*Direction:* {dir_emoji} *{direction}*",
    ]

    entry = trade_data.get("entry_price")
    if entry is not None:
        lines.append(f"*Entry:* `${float(entry):,.4f}`")

    exit_p = trade_data.get("exit_price")
    if exit_p is not None:
        lines.append(f"*Exit:* `${float(exit_p):,.4f}`")

    lines.append(f"*Size:* `{trade_data.get('position_size', 'N/A')}`")

    if trade_data.get("timeframe"):
        lines.append(f"*Timeframe:* `{trade_data['timeframe']}`")

    conf = trade_data.get("confidence_score")
    if conf is not None:
        conf_pct = float(conf) * 100 if float(conf) <= 1 else float(conf)
        lines.append(f"*Confidence:* `{conf_pct:.0f}%`")

    lines.append(f"*Regime:* {regime_label}")

    pnl_abs = trade_data.get("pnl_abs")
    pnl_pct = trade_data.get("pnl_pct")
    if pnl_abs is not None:
        sign = "+" if float(pnl_abs) >= 0 else ""
        pnl_emoji = "💚" if float(pnl_abs) >= 0 else "❤️"
        pnl_line = f"\n{pnl_emoji} *PnL:* `{sign}${float(pnl_abs):,.2f}`"
        if pnl_pct is not None:
            pnl_line += f" (`{sign}{float(pnl_pct):.2f}%`)"
        lines.append(pnl_line)

    rr = trade_data.get("rr_ratio")
    if rr:
        lines.append(f"⚠️ *R/R:* `1:{float(rr):.1f}`")

    indicators = trade_data.get("indicators")
    if indicators and isinstance(indicators, dict):
        lines.append("\n📊 *Indicators*")
        for k, v in list(indicators.items())[:5]:
            lines.append(f"  `{k.upper()}`: {v}")

    ts = trade_data.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    trade_id = trade_data.get("trade_id", "N/A")
    lines += ["", f"📅 `{ts}`", f"🆔 `{trade_id}`"]

    return "\n".join(lines)


def _send_sync(message: str, max_retries: int = 3) -> dict:
    """Send Telegram message synchronously with retry + rate limiting."""
    global _last_sent_time

    if not BOT_TOKEN or not CHAT_ID:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"}

    elapsed = time.time() - _last_sent_time
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)

    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                _last_sent_time = time.time()
                logger.info("Telegram alert sent successfully")
                return {"success": True, "telegram_response": resp.json()}
            else:
                logger.warning(f"Telegram API error (attempt {attempt+1}): {resp.text}")
        except requests.RequestException as exc:
            logger.warning(f"Request failed (attempt {attempt+1}): {exc}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    return {"success": False, "error": f"Failed after {max_retries} attempts"}


async def notify_trade(trade_data: dict, event_type: str = "entry") -> dict:
    """
    Primary async notification function.
    Includes deduplication and rate limiting.
    """
    fp = _fingerprint(event_type, str(trade_data.get("trade_id", "")))
    if fp in _sent_fingerprints:
        logger.info(f"Duplicate suppressed: {trade_data.get('trade_id')} / {event_type}")
        return {"success": False, "error": "Duplicate alert suppressed", "message": ""}

    message = format_trade_message(event_type, trade_data)
    result = await asyncio.to_thread(_send_sync, message)

    if result.get("success"):
        _sent_fingerprints.add(fp)
        if len(_sent_fingerprints) > 1000:
            _sent_fingerprints.clear()

    return {**result, "message": message}


def notify_trade_sync(trade_data: dict, event_type: str = "entry") -> dict:
    """
    Sync wrapper — use this in non-async algo code.
    Example:
        notify_trade_sync({"trade_id": "TRD-001", "symbol": "BTCUSDT", ...}, "entry")
    """
    fp = _fingerprint(event_type, str(trade_data.get("trade_id", "")))
    if fp in _sent_fingerprints:
        return {"success": False, "error": "Duplicate alert suppressed", "message": ""}

    message = format_trade_message(event_type, trade_data)
    result = _send_sync(message)

    if result.get("success"):
        _sent_fingerprints.add(fp)
        if len(_sent_fingerprints) > 1000:
            _sent_fingerprints.clear()

    return {**result, "message": message}


async def on_trade_event(event_type: str, trade_data: dict) -> dict:
    """
    Event-driven entry point. Plug into signal_generator or execution_engine.

    Example integration:
        # In your execution engine:
        from notification_service import on_trade_event

        async def execute_trade(signal):
            # ... your trade logic ...
            await on_trade_event("entry", {
                "trade_id": "TRD-001",
                "symbol": "BTCUSDT",
                "direction": "BUY",
                "entry_price": 67500.00,
                "position_size": 0.05,
                "strategy_name": "Momentum Alpha",
                "confidence_score": 0.82,
                "market_regime": "trend",
                "timeframe": "1h",
                "indicators": {"RSI": "62.3", "MACD": "+0.0012"},
            })
    """
    return await notify_trade(trade_data, event_type)


def send_direct(message: str) -> dict:
    """Send a raw message to Telegram without deduplication (for scheduled summaries)."""
    return _send_sync(message)


async def send_direct_async(message: str) -> dict:
    """Async version of send_direct."""
    return await asyncio.to_thread(_send_sync, message)


def format_daily_summary(summary_type: str, data: dict) -> str:
    """
    Format a comprehensive daily trading summary for Telegram.

    summary_type: "open" (9:15 AM morning recap) or "close" (3:30 PM session close)
    data keys: date_str, total_trades, completed, wins, losses, win_rate,
               total_pnl, avg_pnl, best_trade, worst_trade,
               strategy_stats, regime_counts, open_positions,
               alerts_sent, alerts_failed
    """
    ist_time = data.get("ist_time", "")
    date_str = data.get("date_str", "")

    if summary_type == "open":
        header = "⏰ *MORNING RECAP*"
        subtitle = "Previous Session Performance"
        footer = "\n📌 _Market opens at 09:15 IST. Good luck today!_ 🚀"
    else:
        header = "📊 *SESSION CLOSE REPORT*"
        subtitle = "Today's Full Performance"
        footer = "\n📌 _Market closed at 15:30 IST. See you tomorrow!_ 🌙"

    lines = [
        header,
        f"{subtitle} | `{date_str}` | _{ist_time}_",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    total = data.get("total_trades", 0)
    completed = data.get("completed", 0)
    wins = data.get("wins", 0)
    losses = data.get("losses", 0)
    win_rate = data.get("win_rate", 0)
    total_pnl = data.get("total_pnl", 0)
    avg_pnl = data.get("avg_pnl", 0)
    open_pos = data.get("open_positions", 0)

    if total == 0:
        lines.append("\n_No trades recorded for this session._")
        lines.append(footer)
        return "\n".join(lines)

    pnl_sign = "+" if total_pnl >= 0 else ""
    pnl_emoji = "💚" if total_pnl >= 0 else "❤️"

    lines += [
        f"\n📈 *Performance*",
        f"Events: `{total}` | Closed: `{completed}` | Open: `{open_pos}`",
        f"Win Rate: `{win_rate}%` ({wins}W / {losses}L)",
        f"\n{pnl_emoji} *PnL Summary*",
        f"Total: `{pnl_sign}${abs(total_pnl):,.2f}`",
        f"Average: `{pnl_sign}${abs(avg_pnl):,.2f}` / trade",
    ]

    best = data.get("best_trade")
    worst = data.get("worst_trade")
    if best:
        lines.append(f"Best: `+${best['pnl']:,.2f}` ({best['symbol']} {best['event_type'].upper()})")
    if worst:
        lines.append(f"Worst: `${worst['pnl']:,.2f}` ({worst['symbol']} {worst['event_type'].upper()})")

    strategy_stats = data.get("strategy_stats", {})
    if strategy_stats:
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append("🏆 *Strategy Results*")
        for name, stats in list(strategy_stats.items())[:4]:
            sign = "+" if stats["pnl"] >= 0 else ""
            wr = round(stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
            lines.append(f"{_esc(name)}: `{stats['trades']}tr | {sign}${stats['pnl']:,.0f} | {wr}%`")

    regime_counts = data.get("regime_counts", {})
    if regime_counts:
        total_r = sum(regime_counts.values())
        regime_strs = [f"{k.replace('_', ' ').title()}: `{round(v/total_r*100)}%`" for k, v in regime_counts.items()]
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append("📊 *Market Regimes*")
        lines.append(" | ".join(regime_strs[:4]))

    a_sent = data.get("alerts_sent", 0)
    a_failed = data.get("alerts_failed", 0)
    lines.append(f"\n🔔 *Alerts:* `{a_sent}` sent, `{a_failed}` failed")

    lines.append(footer)
    return "\n".join(lines)
