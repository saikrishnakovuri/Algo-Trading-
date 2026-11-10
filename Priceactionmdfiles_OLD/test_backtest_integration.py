
import sys
import os
from pathlib import Path
import uuid
from datetime import datetime, timezone

# Root path
root = os.path.abspath('..')
sys.path.insert(0, root)

# Mock config
config = {
    'stocks': ['NIFTY'],
    'start_date': '2026-02-01',
    'end_date': '2026-03-01',
    'entry_strategy': 'VWAP_BOUNCE',
    'sl_type': 'ATR_2',
    'tp_type': 'FIX_2R',
    'capital': 1000000,
    'risk_pct': 1.0
}

print("Attempting to import backtest_engine...")
try:
    import backtest_engine
    print(f"Imported from: {backtest_engine.__file__}")
    
    print("Running backtest...")
    result = backtest_engine.run(config)
    print("Backtest completed successfully!")
    print(f"Metrics: {result.get('metrics')}")
    print(f"Trade count: {len(result.get('trades', []))}")
except Exception as e:
    print(f"Backtest FAILED with error: {e}")
    import traceback
    traceback.print_exc()
