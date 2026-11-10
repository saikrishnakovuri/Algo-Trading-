
import sys; sys.path.insert(0,'.')
from modules.options.broker_adapter import get_exchange

tests = [
    ('NIFTY24MAY24050CE', 'NFO'),
    ('BANKNIFTY24MAY45000PE', 'NFO'),
    ('NIFTYFUT', 'NFO'),
    ('NIFTY', 'NSE'),
    ('BANKNIFTY', 'NSE'),
    ('RELIANCE', 'NSE'),
    ('HDFCBANK', 'NSE'),
    ('SBIN', 'NSE'),
]
all_pass = True
for symbol, expected in tests:
    try:
        result = get_exchange(symbol)
        status = 'OK' if result == expected else 'FAIL'
        if status == 'FAIL': all_pass = False
        print(f'  [{status}] {symbol} → {result} (expected {expected})')
    except Exception as e:
        print(f'  [FAIL] {symbol} → Error: {e}')
        all_pass = False

print(f'Exchange routing: {"ALL PASS" if all_pass else "FAILURES FOUND"}')
