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
    
    # State tracking for overrides & trailing
    is_trailing: bool = False
    initial_risk_points: float = 0.0
    trailing_step: int = 1
    human_hints: Optional[Dict] = None

    def mtm(self, price: float) -> float:
        direction = 1 if self.side in {"LONG", "BUY", "CE"} else -1
        return (float(price) - self.entry_price) * self.qty * direction


CLI_HINTS = {
    "direction": None,      # CE or PE
    "sl_points": None,      # Integer points
    "pf_target": None,      # Float multiplier
    "trailing_active": False,
    "regime": None,         # TRENDINGDOWN, TRENDINGUP, CHOPPY
    "force_regime": False,  # True if --force is present
    "time_hint": None,      # HH:MM string
    "force_backtest": False,
    "backtest_start": None,
    "backtest_end": None
}

def parse_cli_hints():
    """
    Pre-parser that intercepts dynamic CLI flags like --SL35, --CE, --14:15 before argparse runs.
    Extracts them into the global CLI_HINTS dictionary and removes them from sys.argv.
    """
    import sys
    import re
    from datetime import datetime
    
    global CLI_HINTS
    args_to_keep = []
    
    # Regex patterns
    sl_pattern = re.compile(r"^--SL(\d+)$", re.IGNORECASE)
    pf_pattern = re.compile(r"^--PF(\d+(?:\.\d+)?)(TSL)?$", re.IGNORECASE)
    time_pattern = re.compile(r"^--(\d{2}:\d{2})$")
    # Matches --force-backtest and optionally --force-backtest--30-12-2025:31-01-2026
    fb_pattern = re.compile(r"^-+force-backtest(?:[-=]+(.+?)[:_]+(.+?))?$", re.IGNORECASE)
    
    for arg in sys.argv:
        sl_match = sl_pattern.match(arg)
        pf_match = pf_pattern.match(arg)
        time_match = time_pattern.match(arg)
        fb_match = fb_pattern.match(arg)
        
        if arg.upper() in ["--CE", "--PE", "--LONG", "--SHORT"]:
            CLI_HINTS["direction"] = arg.upper().replace("--", "")
        elif sl_match:
            CLI_HINTS["sl_points"] = int(sl_match.group(1))
        elif pf_match:
            CLI_HINTS["pf_target"] = float(pf_match.group(1))
            if pf_match.group(2): # TSL suffix present
                CLI_HINTS["trailing_active"] = True
        elif arg.upper() in ["--TRENDINGDOWN", "--TRENDINGUP", "--CHOPPY"]:
            CLI_HINTS["regime"] = arg.upper().replace("--", "")
        elif arg.lower() == "--force":
            CLI_HINTS["force_regime"] = True
        elif time_match:
            CLI_HINTS["time_hint"] = time_match.group(1)
        elif fb_match:
            CLI_HINTS["force_backtest"] = True
            if fb_match.group(1) and fb_match.group(2):
                try:
                    # Support multiple formats like DD-MM-YYYY or YYYY-MM-DD
                    d1_str, d2_str = fb_match.group(1), fb_match.group(2)
                    fmt = "%Y-%m-%d" if len(d1_str.split("-")[0]) == 4 else "%d-%m-%Y"
                    CLI_HINTS["backtest_start"] = datetime.strptime(d1_str, fmt)
                    CLI_HINTS["backtest_end"] = datetime.strptime(d2_str, fmt)
                    
                    # If user enters them backwards, fix it
                    if CLI_HINTS["backtest_start"] > CLI_HINTS["backtest_end"]:
                        CLI_HINTS["backtest_start"], CLI_HINTS["backtest_end"] = CLI_HINTS["backtest_end"], CLI_HINTS["backtest_start"]
                        
                    # Add end of day to backtest_end
                    CLI_HINTS["backtest_end"] = CLI_HINTS["backtest_end"].replace(hour=23, minute=59)
                except Exception:
                    logger.warning("Invalid date format in --force-backtest. Use DD-MM-YYYY:DD-MM-YYYY.")
        elif arg.lower() == "--force-backtest":
            # Simple flag without range
            CLI_HINTS["force_backtest"] = True
        else:
            args_to_keep.append(arg)
            
    # Modify sys.argv so standard argparse doesn't crash on unknown dynamic flags
    sys.argv = args_to_keep

# Run pre-parser immediately upon module import
parse_cli_hints()


class MockMarketFeed:
    """Deterministic async feed for syntax, loop, and risk dry runs."""

    def __init__(self, symbols: List[str], interval_seconds: float = 1.0):
        self.symbols = symbols
        self.interval_seconds = interval_seconds
        self.base_prices = {symbol: 1000.0 + idx * 47.0 for idx, symbol in enumerate(symbols)}
        self.step = 0

    async def events(self, controller: 'LivePaperController') -> AsyncIterator[MarketEvent]:
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


class HistoricalMarketFeed:
    """Async feed that plays back downloaded historical 1m data as ticks and 5m candles, mimicking the live stream."""
    def __init__(self, data_dict: Dict[str, pd.DataFrame], symbols: List[str]):
        self.data_dict = data_dict
        self.symbols = symbols
        
        all_timestamps = set()
        for sym, df in self.data_dict.items():
            all_timestamps.update(df.index)
                    
        self.sorted_timestamps = sorted(list(all_timestamps))

    async def events(self, controller: 'LivePaperController') -> AsyncIterator[MarketEvent]:
        for ts in self.sorted_timestamps:
            is_5m_boundary = ts.minute % 5 == 0
            
            # 1. Yield "ticks" for this timestamp to trigger stoploss/targets
            for symbol in self.symbols:
                df = self.data_dict.get(symbol)
                if df is None or ts not in df.index:
                    continue
                bar = df.loc[ts]
                
                # Yield high/low as ticks to simulate intra-minute volatility
                yield MarketEvent("tick", symbol, f"HIST_{symbol}", ts, float(bar['open']))
                yield MarketEvent("tick", symbol, f"HIST_{symbol}", ts, float(bar['high']))
                yield MarketEvent("tick", symbol, f"HIST_{symbol}", ts, float(bar['low']))
                yield MarketEvent("tick", symbol, f"HIST_{symbol}", ts, float(bar['close']))
                
            # 2. Yield 5-minute candle closes
            if is_5m_boundary:
                for symbol in self.symbols:
                    df = self.data_dict.get(symbol)
                    if df is None: continue
                    
                    df_up_to_now = df.loc[:ts]
                    if df_up_to_now.empty: continue
                    
                    # Ensure we have at least 5 mins of data for a proper candle
                    if len(df_up_to_now) >= 5:
                        last_5_bars = df_up_to_now.tail(5)
                        candle = {
                            "open": float(last_5_bars.iloc[0]['open']),
                            "high": float(last_5_bars['high'].max()),
                            "low": float(last_5_bars['low'].min()),
                            "close": float(last_5_bars.iloc[-1]['close']),
                            "volume": float(last_5_bars['volume'].sum()),
                        }
                        yield MarketEvent("candle_close", symbol, f"HIST_{symbol}", ts, candle["close"], candle)
            
            # No sleep for maximum speed during historical playback
            pass

class AngelOneMarketFeed:
    """Thin async adapter around the existing Angel One broker and in-memory websocket reader."""

    def __init__(self, broker, symbol_tokens: Dict[str, str]):
        from modules.data.memory_data_reader import MemoryDataReader

        self.broker = broker
        self.symbol_tokens = symbol_tokens
        self.reader = MemoryDataReader(broker)
        self.last_candle_ts: Dict[str, datetime] = {}

    async def start(self, controller: 'LivePaperController'):
        tier1 = list(self.symbol_tokens.keys())
        self.reader.initialize_data(self.symbol_tokens, tier1_symbols=tier1)
        self.reader.start_streaming(list(self.symbol_tokens.values()))
        
        # Pre-fill controller frames with 1m history
        logger.info("Pre-filling signal frames with historical data...")
        for symbol, token in self.symbol_tokens.items():
            hist_df = self.reader.get_1m_candles(token, count=300)
            if hist_df is not None and not hist_df.empty:
                controller.frames_1m[symbol] = hist_df
                logger.info("Pre-filled %s with %d historical bars", symbol, len(hist_df))

    async def events(self, controller: 'LivePaperController') -> AsyncIterator[MarketEvent]:
        await self.start(controller)
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
        
        # Apply CLI Regime Force if provided
        if CLI_HINTS["regime"]:
            original_detect = self.selector.context_detector.detect
            def forced_detect(df, vix, current_time=None):
                ctx = original_detect(df, vix, current_time)
                if CLI_HINTS["force_regime"]:
                    ctx.regime = CLI_HINTS["regime"]
                else:
                    # Soft hint (could be used to bump confidence later, but for now we just log it)
                    logger.debug("Regime hint provided (%s) but not forced. System detected: %s", CLI_HINTS["regime"], ctx.regime)
                return ctx
            self.selector.context_detector.detect = forced_detect
            if CLI_HINTS["force_regime"]:
                logger.warning("HARD OVERRIDE: Market regime forced to %s", CLI_HINTS["regime"])
        
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
        self.current_market_time: Optional[datetime] = None
        self._recover_open_positions()

    async def on_tick(self, event: MarketEvent):
        self.latest_prices[event.symbol] = event.ltp
        self.current_market_time = event.ts
        
        # Enforce EOD close if time crosses IST_EOD_CLOSE
        if event.ts.time() >= IST_EOD_CLOSE and not self.block_new_trades:
            await self.close_eod()
            return
        
        pending = self.pending_trades.get(event.symbol)
        if pending and not self.block_new_trades:
            triggered = False
            direction = pending.get("direction") or pending.get("options_direction") or pending.get("signal") or "LONG"
            
            if direction in ["CE", "BUY", "LONG"]:
                if event.ltp >= pending["trigger_high"]:
                    triggered = True
            else:
                if event.ltp <= pending["trigger_low"]:
                    triggered = True
            
            if triggered:
                logger.info("TRIGGER_HIT | %s | Price %.2f broke through trigger", event.symbol, event.ltp)
                pending["entry_price"] = event.ltp
                await self._open_position(event, pending)
                del self.pending_trades[event.symbol]
            else:
                # Verbose debug for forced trades
                if pending.get("strategy") == "MANUAL_FORCE":
                    logger.debug("TICK_CHECK | %s | %s | Price %.2f | TriggerL: %.2f | TriggerH: %.2f", 
                                 event.symbol, direction, event.ltp, pending.get("trigger_low", 0), pending.get("trigger_high", 0))

        # Optimization: Early exit if no active positions to manage
        if not self.positions:
            return

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
        open_positions = [
            {"symbol": pos.symbol, "qty": pos.qty, "side": pos.side, "entry_price": pos.entry_price}
            for pos in self.positions.values() if pos.status == "OPEN"
        ]
        snapshot = await self.portfolio.async_update_unrealized_pnl(open_positions, self.latest_prices)
        if snapshot["circuit_breaker_tripped"]:
            await self.emergency_close_all(snapshot["circuit_breaker_reason"])

    async def _manage_open_positions(self, event: MarketEvent):
        position = self.positions.get(event.symbol)
        if not position or position.status != "OPEN":
            return
            
        is_ce = position.side in {"LONG", "BUY", "CE"}
        
        # Check Stop Loss
        if is_ce and event.ltp <= position.sl:
            await self._close_position(event.symbol, event.ltp, "STOP_LOSS")
            return
        elif not is_ce and event.ltp >= position.sl:
            await self._close_position(event.symbol, event.ltp, "STOP_LOSS")
            return
            
        # Check Target / Trailing
        target_hit = (is_ce and event.ltp >= position.tp) or (not is_ce and event.ltp <= position.tp)
        
        if target_hit:
            if position.is_trailing:
                risk = position.initial_risk_points
                if risk <= 0:
                    await self._close_position(event.symbol, event.ltp, "TARGET")
                    return
                    
                # Calculate new trailing levels
                if is_ce:
                    position.sl = position.entry_price + (risk * (position.trailing_step - 1))
                    position.tp = position.tp + risk
                else:
                    position.sl = position.entry_price - (risk * (position.trailing_step - 1))
                    position.tp = position.tp - risk
                
                position.trailing_step += 1
                logger.info("TRAILING_STEP | %s | Step %d | New SL: %.2f | New TP: %.2f", 
                            event.symbol, position.trailing_step, position.sl, position.tp)
                
                # Update the trade log with new SL/TP
                for t in self.trade_log:
                    if t.get("trade_id") == position.trade_id:
                        t["sl"] = position.sl
                        t["tp"] = position.tp
                        break
                self._persist_trades()
            else:
                await self._close_position(event.symbol, event.ltp, "TARGET")

    async def _open_position(self, event: MarketEvent, signal: Dict):
        if event.symbol in self.positions:
            return
        entry = float(signal.get("entry_price") or event.ltp)
        side = signal.get("direction") or signal.get("options_direction") or signal.get("signal") or "LONG"
        
        # 1. Override SL if provided by Human
        sig_sl = signal.get("sl")
        if CLI_HINTS["sl_points"] is not None:
            if side in ["CE", "LONG", "BUY"]:
                sl = entry - CLI_HINTS["sl_points"]
            else:
                sl = entry + CLI_HINTS["sl_points"]
            logger.info("Human Hint: Overriding SL to %d points (%.2f)", CLI_HINTS["sl_points"], sl)
        elif sig_sl is not None and float(sig_sl) > 0:
            sl = float(sig_sl)
        else:
            # Default direction-aware SL if missing or zero
            if side in ["CE", "LONG", "BUY"]:
                sl = entry * 0.995
            else:
                sl = entry * 1.005
            
        risk_points = abs(entry - sl)
        logger.debug("RISK_CALC | %s | Side: %s | Entry: %.2f | SL: %.2f | RiskPoints: %.2f", 
                     event.symbol, side, entry, sl, risk_points)
        
        # 2. Override TP if provided by Human
        sig_tp = signal.get("tp")
        if CLI_HINTS["pf_target"] is not None:
            pf = CLI_HINTS["pf_target"]
            if side in ["CE", "LONG", "BUY"]:
                tp = entry + (risk_points * pf)
            else:
                tp = entry - (risk_points * pf)
            logger.info("Human Hint: Overriding TP to PF%.1f (%.2f)", pf, tp)
        elif sig_tp is not None and float(sig_tp) > 0:
            tp = float(sig_tp)
        else:
            if side in ["CE", "LONG", "BUY"]:
                tp = entry * 1.01
            else:
                tp = entry * 0.99

        qty = self.risk_manager.get_position_size(event.symbol, entry, risk_points)
        risk_amount = qty * risk_points
        if qty <= 0 or risk_amount <= 0:
            logger.warning("ENTRY_REJECTED | %s | Invalid qty (%d) or risk (%.2f)", event.symbol, qty, risk_amount)
            return
        if not await self.portfolio.async_can_enter_trade(risk_amount):
            logger.warning("ENTRY_REJECTED | %s | Portfolio risk block for %.2f", event.symbol, risk_amount)
            return

        # Capture used hints
        hints_used = {k: v for k, v in CLI_HINTS.items() if v is not None and v is not False}

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
            is_trailing=CLI_HINTS["trailing_active"],
            initial_risk_points=risk_points,
            human_hints=hints_used if hints_used else None
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
        if self.current_market_time:
            position.closed_at = self.current_market_time.isoformat()
        else:
            position.closed_at = datetime.now().isoformat()
        position.pnl = round(position.mtm(price), 2)
        await self.portfolio.async_update_equity(position.pnl)
        self.portfolio.remove_risk(position.risk_amount)
        self.trade_log.append(asdict(position))
        self._persist_trades()
        logger.info("PAPER_EXIT | %s | pnl=%.2f | %s", symbol, position.pnl, reason)

        # Human Intuition Logging (Permanent Machine Learning Dataset)
        if reason == "TARGET" and position.human_hints:
            self._log_human_intuition_win(position)
    def _log_human_intuition_win(self, position: PaperPosition):
        log_file = Path("data/human_intuition_wins.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        data = []
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        data.append(asdict(position))
        log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Human Intuition Win permanently logged for %s", position.symbol)

    def _append_candle(self, symbol: str, ts: datetime, candle: Dict[str, float]):
        row = pd.DataFrame([candle], index=[ts])
        frame = pd.concat([self.frames_1m.get(symbol, pd.DataFrame()), row])
        frame = frame[~frame.index.duplicated(keep="last")].sort_index().tail(300)
        frame.columns = [c.lower() for c in frame.columns]
        self.frames_1m[symbol] = frame

    def _build_signal(self, symbol: str) -> Optional[Dict]:
        df_1m = self.frames_1m.get(symbol)
        if df_1m is None:
            logger.debug("SIGNAL_CHECK | %s | No 1m data", symbol)
            return None
        
        logger.debug("SIGNAL_CHECK | %s | 1m bars: %d", symbol, len(df_1m))
        if len(df_1m) < 20:
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
        
        signal = None
        if memory_signal:
            memory_signal["symbol"] = symbol
            memory_signal["strategy"] = "MARKET_MEMORY"
            signal = memory_signal
        else:
            signal = self.selector.select_best_signal(df_5m, symbol, vix=15.0, current_time=df_1m.index[-1], mode="BALANCED")
            
        if not signal:
            # Handle Manual Force: If math finds nothing but user says --force --PE --10:30
            if CLI_HINTS["force_regime"] and CLI_HINTS["direction"] and CLI_HINTS["time_hint"]:
                try:
                    hint_time = datetime.strptime(CLI_HINTS["time_hint"], "%H:%M").time()
                    curr_time = df_1m.index[-1].time()
                    hint_dt = datetime.combine(datetime.today(), hint_time)
                    curr_dt = datetime.combine(datetime.today(), curr_time)
                    diff = abs((curr_dt - hint_dt).total_seconds())
                    if diff <= 300: # Within 5 mins of forced time
                        logger.warning("MANUAL_FORCE | %s | Creating forced %s signal at %s", 
                                       symbol, CLI_HINTS["direction"], CLI_HINTS["time_hint"])
                        signal = {
                            "symbol": symbol,
                            "strategy": "MANUAL_FORCE",
                            "direction": CLI_HINTS["direction"],
                            "entry_price": float(df_1m.iloc[-1]["close"]),
                            "sl": 0, "tp": 0, "confidence": 100.0
                        }
                except Exception:
                    pass

            if not signal:
                return None

        # Apply Human Intuition Filters (Direction and Timing) for ALGORITHMIC signals
        # If it's a MANUAL_FORCE signal, we bypass these filters since they are already part of the force logic
        if signal.get("strategy") != "MANUAL_FORCE":
            if CLI_HINTS["time_hint"]:
                # Check if current time is within +/- 10 mins of the hint
                try:
                    hint_time = datetime.strptime(CLI_HINTS["time_hint"], "%H:%M").time()
                    curr_time = df_1m.index[-1].time()
                    hint_dt = datetime.combine(datetime.today(), hint_time)
                    curr_dt = datetime.combine(datetime.today(), curr_time)
                    diff = abs((curr_dt - hint_dt).total_seconds())
                    if diff > 600: # 10 minutes
                        return None
                except ValueError:
                    pass # Invalid time format, ignore filter

            if CLI_HINTS["direction"]:
                sig_dir = signal.get("direction", "").upper()
                if CLI_HINTS["direction"] in ["CE", "LONG", "BUY"]:
                    if sig_dir not in ["CE", "LONG", "BUY"]:
                        return None
                elif CLI_HINTS["direction"] in ["PE", "SHORT", "SELL"]:
                    if sig_dir not in ["PE", "SHORT", "SELL"]:
                        return None

        return signal
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
                    is_trailing=bool(trade.get("is_trailing", False)),
                    initial_risk_points=float(trade.get("initial_risk_points", 0.0)),
                    trailing_step=int(trade.get("trailing_step", 1)),
                    human_hints=trade.get("human_hints", None)
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
        """Asynchronously writes trade logs to disk to avoid blocking the event loop."""
        import asyncio
        import json
        
        def write_sync():
            self.trade_file.parent.mkdir(parents=True, exist_ok=True)
            self.trade_file.write_text(json.dumps(self.trade_log, indent=2), encoding="utf-8")
        
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, write_sync)

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


def is_market_open_ist() -> bool:
    """Checks if the current time in IST is within market hours (09:15 - 15:30 on weekdays)."""
    now_utc = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = now_utc + ist_offset
    
    if now_ist.weekday() >= 5: # Saturday or Sunday
        return False
        
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= now_ist <= market_close


async def run_controller(args):
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else load_symbols(args.symbol_limit)
    symbol_tokens = load_symbol_tokens(symbols)
    starting_capital = args.capital if args.reset_capital else LivePaperController._get_latest_equity(args.capital)
    controller = LivePaperController(starting_capital, symbols, symbol_tokens, trade_file=Path(args.trade_file))

    if args.feed == "angel":
        is_live_hours = is_market_open_ist()
        if CLI_HINTS["force_backtest"]:
            is_live_hours = False
            logger.info("Forcing BACKTEST mode via CLI argument.")
            
        if is_live_hours:
            logger.info("Market is OPEN. Initializing LIVE Angel One websocket feed.")
            from modules.broker_layer import AngelOneBroker

            broker = AngelOneBroker()
            if not broker.login():
                raise RuntimeError("Angel One login failed; check .env credentials.")
            if not symbol_tokens:
                raise RuntimeError("No broker tokens found for requested symbols.")
            feed = AngelOneMarketFeed(broker, symbol_tokens)
        else:
            logger.info("Market is CLOSED (or forced). Initializing HISTORICAL backtest feed.")
            from pulling_history import pull_historical_data
            
            # Use requested date range from CLI or default to None (which fetches last 2 days)
            start_dt = CLI_HINTS["backtest_start"]
            end_dt = CLI_HINTS["backtest_end"]
            
            # Fetch data using the new module
            data_dict = pull_historical_data(symbols, start_date=start_dt, end_date=end_dt)
            if not data_dict:
                raise RuntimeError("Failed to fetch historical data for backtest.")
            
            feed = HistoricalMarketFeed(data_dict, symbols)
            
            # Crucial: Override market hours check so the backtest loop doesn't immediately exit
            args.ignore_market_hours = True 
    else:
        feed = MockMarketFeed(symbols, interval_seconds=args.mock_interval)

    stop_at = datetime.now() + timedelta(seconds=args.dry_run_seconds) if args.dry_run_seconds else None
    async for event in feed.events(controller):
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
    parser.add_argument("--force-backtest", action="store_true", help="Forces historical backtest simulation even during live market hours.")
    parser.add_argument("--reset-capital", action="store_true")
    parser.add_argument("--trade-file", default="data/live_paper_trades.json")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_controller(parse_args()))
