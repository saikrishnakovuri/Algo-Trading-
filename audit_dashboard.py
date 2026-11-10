
import requests, json

base = 'http://localhost:8000'
tests = {
    'Bot Status':       f'{base}/api/live/status',
    'Live Positions':   f'{base}/api/live/positions',
    'Analytics':        f'{base}/api/analytics/summary',
    'Strategy Perf':    f'{base}/api/analytics/strategy-perf',
    'Settings':         f'{base}/api/settings',
    'Live Context':     f'{base}/api/live/context',
    'Command History':  f'{base}/api/control/command-history',
    'Backtest History': f'{base}/api/backtest/history',
}
print('Dashboard API Status:')
for name, url in tests.items():
    try:
        r = requests.get(url, timeout=3)
        print(f'  [{r.status_code}] {name}: OK')
    except Exception as e:
        print(f'  [ERR] {name}: OFFLINE')
