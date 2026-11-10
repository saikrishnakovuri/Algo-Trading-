import argparse
import asyncio
import json
import logging
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import pandas as pd
import yaml

from modules.options.risk_manager import OptionsRiskManager
from modules.portfolio_manager import PortfolioManager
from modules.smc.engine import SmartMoneyConceptsEngine
from modules.strategy_selector import MasterStrategySelector


IST_MARKET_OPEN = time(9, 15)
IST_ENTRY_STOP = time(15, 15)
IST_EOD_CLOSE = time(15, 25)
DEFAULT_TRADE_FILE = Path("data/live_paper_trades.json")
REPORT_DIR = Path("reports/live_paper")
MEMORY_STATE_FILE = Path("data/market_memory_state.json")


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/live_paper_controller.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("live_paper_controller")


@dataclass
class MarketEvent:
    event_type: str
    symbol: str
    token: str
    ts: datetime
    ltp: float
    candle: Optional[Dict[str, float]] = None


@dataclass
class PaperPosition:
    trade_id: str
    symbol: str
    token: str
    side: str
    qty: int
    entry_price: float
    sl: float
    tp: float
    opened_at: str
    strategy: str
    risk_amount: float
    status: str = "OPEN"
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    closed_at: Optional[str] = None
    pnl: float = 0.0

    def mtm(self, price: float) -> float:
        direction = 1 if self.side in {"LONG", "BUY", "CE"} else -1
        return (float(price) - self.entry_price) * self.qty * direction


class MockMarketFeed:
    """Deterministic async feed for syntax, loop, and risk dry runs."""

    def __init__(self, symbols: List[str], interval_seconds: float = 1.0):
        self.symbols = symbols
        self.interval_seconds = interval_seconds
        self.base_prices = {symbol: 1000.0 + idx * 47.0 for idx, symbol in enumerate(symbols)}
        self.step = 0

    async def events(self) -> AsyncIterator[MarketEvent]:
        while True:
            self.step += 1
            now = datetime.now()
            for idx, symbol in enumerate(self.symbols):
                wave = math.sin((self.step + idx) / 7.0) * 2.5
                drift = (self.step % 20) * 0.08
                ltp = round(self.base_prices[symbol] + wave + drift, 2)
                token = f"MOCK_{symbol}"
                yield MarketEvent("tick", symbol, token, now, ltp)

                if self.step % 5 == 0:
                    candle = {
                        "open": round(ltp - 0.6, 2),
                        "high": round(ltp + 1.4, 2),
                        "low": round(ltp - 1.8, 2),
                        "close": ltp,
                        "volume": 1000 + self.step * 5,
                    }
                    yield MarketEvent("candle_close", symbol, token, now, ltp, candle)
            await asyncio.sleep(self.interval_seconds)


class AngelOneMarketFeed:
    """Thin async adapter around the existing Angel One broker and in-memory websocket reader."""

    def __init__(self, broker, symbol_tokens: Dict[str, str]):
        from modules.data.memory_data_reader import MemoryDataReader

        self.broker = broker
        self.symbol_tokens = symbol_tokens
        self.reader = MemoryDataReader(broker)
        self.last_candle_ts: Dict[str, datetime] = {}

    async def start(self):
        tier1 = list(self.symbol_tokens.keys())
        self.reader.initialize_data(self.symbol_tokens, tier1_symbols=tier1)
        self.reader.start_streaming(list(self.symbol_tokens.values()))

    async def events(self) -> AsyncIterator[MarketEvent]:
        await self.start()
        while True:
            now = datetime.now()
            for symbol, token in self.symbol_tokens.items():
                live = self.reader.get_live_price(token)
                if live and live.get("ltp"):
                    yield MarketEvent("tick", symbol, token, now, float(live["ltp"]))

                df = self.reader.get_5m_candles(token, 2)
                if df is not None and not df.empty:
                    candle_ts = df.index[-1].to_pydatetime()
                    if self.last_candle_ts.get(symbol) != candle_ts:
                        self.last_candle_ts[symbol] = candle_ts
                        row = df.iloc[-1]
                        candle = {
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row.get("volume", 0)),
                        }
                        yield MarketEvent("candle_close", symbol, token, candle_ts, candle["close"], candle)
            await asyncio.sleep(1)


class LivePaperController:
    def __init__(self, starting_capital: float, symbols: List[str], symbol_tokens: Dict[str, str], trade_file: Path = DEFAULT_TRADE_FILE):
        self.portfolio = PortfolioManager(initial_capital=starting_capital)
        self.risk_manager = OptionsRiskManager(total_capital=starting_capital)
        self.smc_engine = SmartMoneyConceptsEngine()
        self.selector = MasterStrategySelector()
        self._load_memory_state()
        self.symbols = symbols
        self.symbol_tokens = symbol_tokens
        self.positions: Dict[str, PaperPosition] = {}
        self.latest_prices: Dict[str, float] = {}
        self.frames_1m: Dict[str, pd.DataFrame] = {}
        self.pending_trades: Dict[str, Dict] = {}
        self.block_new_trades = False
        self.trade_file = trade_file
        self.trade_log: List[Dict] = self._load_trade_log()
        self._recover_open_positions()

    async def on_tick(self, event: MarketEvent):
        self.latest_prices[event.symbol] = event.ltp
        
        pending = self.pending_trades.get(event.symbol)
        if pending and not self.block_new_trades:
            triggered = False
            direction = pending.get("direction") or pending.get("options_direction") or pending.get("signal") or "LONG"
            if direction in ["CE", "BUY", "LONG"]:
                if event.ltp > pending["trigger_high"]:
                    triggered = True
            else:
                if event.ltp < pending["trigger_low"]:
                    triggered = True
            
            if triggered:
                pending["entry_price"] = event.ltp
                await self._open_position(event, pending)
                del self.pending_trades[event.symbol]

        await self._mark_to_market()
        await self._manage_open_positions(event)

    async def on_candle_close(self, event: MarketEvent):
        if not event.candle:
            return
        self._append_candle(event.symbol, event.ts, event.candle)
        try:
            if self.block_new_trades or event.ts.time() >= IST_ENTRY_STOP:
                return

            # Discard any pending trade that wasn't triggered in the previous 5m candle
            if event.symbol in self.pending_trades:
                del self.pending_trades[event.symbol]

            signal = self._build_signal(event.symbol)
            if not signal:
                return
            
            # Require 1-minute confirmation breakout instead of immediate entry
            signal["trigger_high"] = float(event.candle["high"])
            signal["trigger_low"] = float(event.candle["low"])
            signal["signal_time"] = event.ts.isoformat()
            
            self.pending_trades[event.symbol] = signal
            logger.info("SIGNAL_PENDING | %s | %s | Waiting for breakout (High: %.2f, Low: %.2f)", 
                        event.symbol, signal.get("strategy", "UNKNOWN"), signal["trigger_high"], signal["trigger_low"])
        finally:
            self._save_memory_state()

    async def emergency_close_all(self, reason: str):
        if not self.positions:
            return
        logger.error("EMERGENCY_CLOSE_ALL | %s", reason)
        self.block_new_trades = True
        for symbol in list(self.positions.keys()):
            price = self.latest_prices.get(symbol, self.positions[symbol].entry_price)
            await self._close_position(symbol, price, reason)

    async def close_eod(self):
        self.block_new_trades = True
        for symbol in list(self.positions.keys()):
            price = self.latest_prices.get(symbol, self.positions[symbol].entry_price)
            await self._close_position(symbol, price, "EOD_CLOSE")
        self._save_memory_state()
        self._write_summary()

    async def _mark_to_market(self):
        open_positions = [asdict(pos) for pos in self.positions.values() if pos.status == "OPEN"]
        snapshot = await self.portfolio.async_update_unrealized_pnl(open_positions, self.latest_prices)
        if snapshot["circuit_breaker_tripped"]:
            await self.emergency_close_all(snapshot["circuit_breaker_reason"])

    async def _manage_open_positions(self, event: MarketEvent):
        position = self.positions.get(event.symbol)
        if not position or position.status != "OPEN":
            return
        if position.side in {"LONG", "BUY", "CE"}:
            if event.ltp <= position.sl:
                await self._close_position(event.symbol, event.ltp, "STOP_LOSS")
            elif event.ltp >= position.tp:
                await self._close_position(event.symbol, event.ltp, "TARGET")
        else:
            if event.ltp >= position.sl:
                await self._close_position(event.symbol, event.ltp, "STOP_LOSS")
            elif event.ltp <= position.tp:
                await self._close_position(event.symbol, event.ltp, "TARGET")

    async def _open_position(self, event: MarketEvent, signal: Dict):
        if event.symbol in self.positions:
            return
        entry = float(signal.get("entry_price") or event.ltp)
        sl = float(signal.get("sl") or entry * 0.995)
        tp = float(signal.get("tp") or entry * 1.01)
        side = signal.get("direction") or signal.get("options_direction") or signal.get("signal") or "LONG"
        risk_points = abs(entry - sl)
        qty = self.risk_manager.get_position_size(event.symbol, entry, risk_points)
        risk_amount = qty * risk_points
        if qty <= 0 or risk_amount <= 0:
            return
        if not await self.portfolio.async_can_enter_trade(risk_amount):
            logger.info("TRADE_BLOCKED | %s | risk %.2f", event.symbol, risk_amount)
            return

        trade_id = f"{event.symbol}_{event.ts.strftime('%Y%m%d_%H%M%S')}"
        position = PaperPosition(
            trade_id=trade_id,
            symbol=event.symbol,
            token=event.token,
            side=side,
            qty=qty,
            entry_price=entry,
            sl=sl,
            tp=tp,
            opened_at=event.ts.isoformat(),
            strategy=signal.get("strategy", "MARKET_MEMORY"),
            risk_amount=risk_amount,
        )
        self.positions[event.symbol] = position
        self.trade_log.append(asdict(position))
        self._persist_trades()
        logger.info("PAPER_ENTRY | %s | %s qty=%s entry=%.2f sl=%.2f tp=%.2f", event.symbol, side, qty, entry, sl, tp)

    async def _close_position(self, symbol: str, price: float, reason: str):
        position = self.positions.pop(symbol, None)
        if not position:
            return
        position.status = "CLOSED"
        position.exit_price = float(price)
        position.exit_reason = reason
        position.closed_at = datetime.now().isoformat()
        position.pnl = round(position.mtm(price), 2)
        await self.portfolio.async_update_equity(position.pnl)
        self.portfolio.remove_risk(position.risk_amount)
        self.trade_log.append(asdict(position))
        self._persist_trades()
        logger.info("PAPER_EXIT | %s | pnl=%.2f | %s", symbol, position.pnl, reason)

    def _append_candle(self, symbol: str, ts: datetime, candle: Dict[str, float]):
        row = pd.DataFrame([candle], index=[ts])
        frame = pd.concat([self.frames_1m.get(symbol, pd.DataFrame()), row])
        frame = frame[~frame.index.duplicated(keep="last")].sort_index().tail(300)
        frame.columns = [c.lower() for c in frame.columns]
        self.frames_1m[symbol] = frame

    def _build_signal(self, symbol: str) -> Optional[Dict]:
        df_1m = self.frames_1m.get(symbol)
        if df_1m is None or len(df_1m) < 20:
            return None
        df_5m = df_1m.resample("5min").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        if df_5m.empty:
            return None

        prior = self._prior_session_ohlc(df_1m)
        preopen = {"high": prior["high"], "low": prior["low"]}
        atr_1m = self._atr(df_1m)
        atr_5m = self._atr(df_5m)
        smc_state = self.smc_engine.update(symbol, df_5m, df_1m, prior, preopen, atr_5m, atr_1m)
        self.selector.market_memory.ingest_smc_state(symbol, smc_state, current_idx=len(df_1m) - 1, timestamp=df_1m.index[-1])
        self.selector.market_memory.update(symbol, df_1m)
        memory_signal = self.selector.market_memory.ready_signal(symbol, df_1m)
        if memory_signal:
            memory_signal["symbol"] = symbol
            memory_signal["strategy"] = "MARKET_MEMORY"
            return memory_signal
        return self.selector.select_best_signal(df_5m, symbol, vix=15.0, current_time=df_1m.index[-1], mode="BALANCED")

    def _prior_session_ohlc(self, df: pd.DataFrame) -> Dict[str, float]:
        return {
            "high": float(df["high"].tail(60).max()),
            "low": float(df["low"].tail(60).min()),
            "close": float(df["close"].iloc[-1]),
        }

    def _atr(self, df: pd.DataFrame, period: int = 14) -> float:
        if len(df) < 2:
            return 0.0
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.tail(period).mean())

    def _load_trade_log(self) -> List[Dict]:
        if self.trade_file.exists():
            try:
                return json.loads(self.trade_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Existing trade log is invalid JSON; starting fresh.")
        return []

    def _recover_open_positions(self):
        closed_trade_ids = {
            trade.get("trade_id")
            for trade in self.trade_log
            if trade.get("status") == "CLOSED" and trade.get("trade_id")
        }
        recovered = 0
        for trade in self.trade_log:
            if trade.get("status") != "OPEN":
                continue
            if trade.get("trade_id") in closed_trade_ids:
                continue
            try:
                position = PaperPosition(
                    trade_id=str(trade["trade_id"]),
                    symbol=str(trade["symbol"]),
                    token=str(trade.get("token", "")),
                    side=str(trade.get("side", "LONG")),
                    qty=int(trade["qty"]),
                    entry_price=float(trade["entry_price"]),
                    sl=float(trade["sl"]),
                    tp=float(trade["tp"]),
                    opened_at=str(trade.get("opened_at", "")),
                    strategy=str(trade.get("strategy", "MARKET_MEMORY")),
                    risk_amount=float(trade.get("risk_amount", 0.0)),
                    status="OPEN",
                    exit_price=trade.get("exit_price"),
                    exit_reason=trade.get("exit_reason"),
                    closed_at=trade.get("closed_at"),
                    pnl=float(trade.get("pnl", 0.0)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping invalid open paper trade during recovery: %s", exc)
                continue
            self.positions[position.symbol] = position
            recovered += 1

        if recovered:
            self.portfolio.active_risk = sum(pos.risk_amount for pos in self.positions.values())
            logger.warning("Recovered %d open paper position(s) from %s", recovered, self.trade_file)

    def _persist_trades(self):
        self.trade_file.parent.mkdir(parents=True, exist_ok=True)
        self.trade_file.write_text(json.dumps(self.trade_log, indent=2), encoding="utf-8")

    def _write_summary(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        summary = {
            "generated_at": datetime.now().isoformat(),
            "portfolio": self.portfolio.snapshot(),
            "open_positions": [asdict(pos) for pos in self.positions.values()],
            "trade_events": len(self.trade_log),
        }
        path = REPORT_DIR / f"summary_{datetime.now().strftime('%Y%m%d')}.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        logger.info("Daily summary written to %s", path)

    def _load_memory_state(self):
        if self.selector.market_memory.load_state(str(MEMORY_STATE_FILE)):
            logger.warning("Recovered market narrative memory from %s", MEMORY_STATE_FILE)

    def _save_memory_state(self):
        try:
            self.selector.market_memory.save_state(str(MEMORY_STATE_FILE))
        except OSError as exc:
            logger.error("Failed to save market narrative memory: %s", exc)

    @staticmethod
    def _get_latest_equity(fallback_capital: float) -> float:
        if not REPORT_DIR.exists():
            return fallback_capital
        summaries = list(REPORT_DIR.glob("summary_*.json"))
        if not summaries:
            return fallback_capital
        latest = max(summaries, key=lambda path: path.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
            equity = payload.get("portfolio", {}).get("total_equity")
            if equity is None:
                return fallback_capital
            equity = float(equity)
            if equity <= 0:
                return fallback_capital
            logger.info("Auto-resume equity %.2f from %s", equity, latest)
            return equity
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Could not auto-resume equity from %s: %s", latest, exc)
            return fallback_capital


def load_symbols(limit: int) -> List[str]:
    with open("config/universe.yaml", "r", encoding="utf-8") as f:
        universe = yaml.safe_load(f)["universe"]["mappings"]
    return list(universe.keys())[:limit]


def load_symbol_tokens(symbols: List[str]) -> Dict[str, str]:
    if not Path("broker_tokens.json").exists():
        return {}
    with open("broker_tokens.json", "r", encoding="utf-8") as f:
        tokens = json.load(f)
    resolved = {}
    for symbol in symbols:
        token = tokens.get(f"{symbol}-EQ") or tokens.get(symbol)
        if token:
            resolved[symbol] = str(token)
    return resolved


async def run_controller(args):
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else load_symbols(args.symbol_limit)
    symbol_tokens = load_symbol_tokens(symbols)
    starting_capital = args.capital if args.reset_capital else LivePaperController._get_latest_equity(args.capital)
    controller = LivePaperController(starting_capital, symbols, symbol_tokens, trade_file=Path(args.trade_file))

    if args.feed == "angel":
        from modules.broker_layer import AngelOneBroker

        broker = AngelOneBroker()
        if not broker.login():
            raise RuntimeError("Angel One login failed; check .env credentials.")
        if not symbol_tokens:
            raise RuntimeError("No broker tokens found for requested symbols.")
        feed = AngelOneMarketFeed(broker, symbol_tokens)
    else:
        feed = MockMarketFeed(symbols, interval_seconds=args.mock_interval)

    stop_at = datetime.now() + timedelta(seconds=args.dry_run_seconds) if args.dry_run_seconds else None
    async for event in feed.events():
        now = datetime.now()
        if stop_at and now >= stop_at:
            break
        if not args.ignore_market_hours and now.time() >= IST_EOD_CLOSE:
            break
        if event.event_type == "tick":
            await controller.on_tick(event)
        elif event.event_type == "candle_close":
            await controller.on_candle_close(event)
    await controller.close_eod()


def parse_args():
    parser = argparse.ArgumentParser(description="Live paper trading controller for the Market Narrative Engine.")
    parser.add_argument("--feed", choices=["mock", "angel"], default=os.getenv("LIVE_PAPER_FEED", "mock"))
    parser.add_argument("--capital", type=float, default=500000.0)
    parser.add_argument("--symbol-limit", type=int, default=30)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--dry-run-seconds", type=int, default=300)
    parser.add_argument("--mock-interval", type=float, default=1.0)
    parser.add_argument("--ignore-market-hours", action="store_true")
    parser.add_argument("--reset-capital", action="store_true")
    parser.add_argument("--trade-file", default="data/live_paper_trades.json")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_controller(parse_args()))
