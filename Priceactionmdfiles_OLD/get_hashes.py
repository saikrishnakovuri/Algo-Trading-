import hashlib
import os

files = [
    '../live_options_trader.py',
    '../main_backtest.py',
    '../modules/strategy_mapper.py',
    '../modules/strategy_selector.py',
    '../modules/v3_utils.py',
    '../modules/candlestick_engine.py',
    '../modules/risk_guard.py',
    'live_options_trader.py',
    'main_backtest.py',
    'modules/strategy_mapper.py',
    'modules/strategy_selector.py',
    'modules/v3_utils.py',
    'modules/candlestick_engine.py',
    'modules/risk_guard.py'
]

hashes = {}
for f in files:
    if os.path.exists(f):
        hashes[f] = hashlib.md5(open(f, "rb").read()).hexdigest()
        print(f"{f}: {hashes[f]}")
    else:
        # Don't print if not found, to keep it clean, or just print NOT FOUND
        pass
