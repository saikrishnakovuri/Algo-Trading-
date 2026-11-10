
import sys; sys.path.insert(0,'.')
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate realistic NIFTY-like test data (100 bars of 5m)
np.random.seed(42)
base = 24000
prices = base + np.cumsum(np.random.randn(100) * 30)
dates = pd.date_range('2026-05-05 09:15', periods=100, freq='5min')
df = pd.DataFrame({
    'open':   prices * 0.9995,
    'high':   prices * 1.001,
    'low':    prices * 0.999,
    'close':  prices,
    'volume': np.random.randint(1000, 5000, 100)
}, index=dates)

# Test each engine
from modules.strategy_selector import MasterStrategySelector
selector = MasterStrategySelector()

print('Engine Test Results:')
print('-' * 50)
for name, engine in selector.engines.items():
    try:
        if name == 'SMC_CORE':
             # Skip or use correct parameters if known, but user script had this:
             # selector._call_engine(name, engine, df, 'NIFTY', None)
             # Let's try to mock the parameters for SMC_CORE if possible or just handle error
             pass
             
        result = selector._call_engine(name, engine, df, 'NIFTY', None)
        status = 'SIGNAL' if result else 'No signal (normal)'
        print(f'{name}: {status}')
    except Exception as e:
        print(f'{name}: ERROR - {e}')
print('-' * 50)
