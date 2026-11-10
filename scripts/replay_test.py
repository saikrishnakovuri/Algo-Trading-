"""
Future-blind replay validator for MasterStrategySelector and MarketMemoryEngine.

Example:
    python scripts/replay_test.py --csv data/nifty_30d.csv --symbol NIFTY

Optional memory sanity check:
    python scripts/replay_test.py --csv data/nifty_30d.csv --symbol NIFTY --inject-demo-memory-event
"""

import argparse
import logging
import os
import sys
from typing import Optional

import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.strategy_selector import MasterStrategySelector


REQUIRED_COLUMNS = ("open", "high", "low", "close")


def load_ohlcv(csv_path: str, time_col: Optional[str] = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [str(c).lower() for c in df.columns]

    if time_col:
        time_key = time_col.lower()
    else:
        time_key = next((c for c in ("datetime", "timestamp", "date", "time") if c in df.columns), None)

    if time_key:
        df[time_key] = pd.to_datetime(df[time_key])
        df = df.set_index(time_key).sort_index()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("CSV missing required OHLC columns: %s" % ", ".join(missing))

    if "volume" not in df.columns:
        df["volume"] = 0

    return df


def replay(
    df: pd.DataFrame,
    symbol: str,
    vix: float,
    min_bars: int,
    inject_demo_memory_event: bool = False,
) -> None:
    selector = MasterStrategySelector()
    signals = []

    for end in range(min_bars, len(df) + 1):
        window = df.iloc[:end].copy()

        if inject_demo_memory_event and end == 10:
            level = float(window["high"].iloc[-2])
            selector.market_memory.ingest_events(
                symbol,
                [{
                    "type": "wick_break",
                    "direction": "BULL",
                    "level": level,
                    "invalidation_level": float(window["low"].iloc[-5:end].min()),
                    "bar_idx": end - 1,
                    "source": "REPLAY_DEMO_WICK",
                    "expiry_bars": 20,
                    "retest_expiry_bars": 20,
                }],
                current_idx=end - 1,
                timestamp=window.index[-1],
            )

        signal = selector.select_best_signal(window, symbol=symbol, vix=vix, current_time=window.index[-1])
        active_memory = selector.market_memory.active_setups(symbol)

        if end in (10, 25) or signal:
            print(
                "bar=%s time=%s active_memory=%s signal=%s"
                % (
                    end,
                    window.index[-1],
                    len(active_memory),
                    None if not signal else "%s:%s:%s" % (
                        signal.get("strategy"),
                        signal.get("direction"),
                        signal.get("confidence"),
                    ),
                )
            )

        if signal:
            signals.append((end, window.index[-1], signal))

    print("replay_complete bars=%s signals=%s completed_memory=%s" % (
        len(df),
        len(signals),
        len(selector.market_memory.completed),
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run future-blind candle replay.")
    parser.add_argument("--csv", required=True, help="OHLCV CSV path")
    parser.add_argument("--symbol", default="NIFTY", help="Symbol name")
    parser.add_argument("--vix", type=float, default=15.0, help="VIX value to pass into selector")
    parser.add_argument("--min-bars", type=int, default=30, help="Minimum bars before selector starts")
    parser.add_argument("--time-col", default=None, help="Optional timestamp column name")
    parser.add_argument(
        "--inject-demo-memory-event",
        action="store_true",
        help="Inject a demo wick-break at bar 10 to verify memory persists by bar 25.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    df = load_ohlcv(args.csv, time_col=args.time_col)
    replay(
        df=df,
        symbol=args.symbol,
        vix=args.vix,
        min_bars=args.min_bars,
        inject_demo_memory_event=args.inject_demo_memory_event,
    )


if __name__ == "__main__":
    main()
