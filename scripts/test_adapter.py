import sys
import os
import yaml
from pathlib import Path

# Add project root to sys path so we can import 'modules'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CFG_PATH = Path("config/data_source.yaml")


def main():
    if len(sys.argv) < 5:
        print("Usage: python scripts/test_adapter.py <adapter_name> <symbol> <timeframe> <count>")
        sys.exit(1)

    adapter_name, symbol, timeframe, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

    # Force the requested adapter temporarily
    cfg = yaml.safe_load(open(CFG_PATH)) if CFG_PATH.exists() else {}
    cfg["active_adapter"] = adapter_name
    yaml.safe_dump(cfg, open(CFG_PATH, "w"))

    from modules.data_adapters import get_active_adapter
    adapter = get_active_adapter(force_reload=True)

    print(f"\n[TEST] Adapter loaded: {adapter}")
    print(f"[TEST] Requesting: symbol={symbol} timeframe={timeframe} count={count}")

    # Bars
    df = adapter.get_bars(symbol, timeframe, count)
    print(f"\n[TEST] Returned {len(df)} bars")
    print(df.head(3).to_string())
    print("...")
    print(df.tail(3).to_string())

    # Live price
    px = adapter.get_live_price(symbol)
    print(f"\n[TEST] Live price for {symbol}: {px}")

    # Instrument info
    info = adapter.get_instrument_info(symbol)
    print(f"\n[TEST] Instrument info: {info}")

    # Market hours
    hours = adapter.get_market_hours()
    print(f"\n[TEST] Market hours: open={hours.market_open} close={hours.market_close} 24x7={hours.is_24x7}")

    # Health
    health = adapter.health_check()
    print(f"\n[TEST] Health: {health}")

    # Assertions
    assert len(df) > 0, "FAIL: get_bars returned empty DataFrame"
    assert set(["open","high","low","close","volume"]).issubset(df.columns), "FAIL: missing OHLCV columns"
    assert df["close"].iloc[-1] > 0, "FAIL: latest close is non-positive"
    assert px > 0, "FAIL: live price is non-positive"
    assert health["status"] in ("OK","DEGRADED"), f"FAIL: health status = {health['status']}"

    print(f"\n[TEST] ✅ All assertions passed.")


if __name__ == "__main__":
    main()
