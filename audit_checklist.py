
import sys; sys.path.insert(0,'.')
import requests
from modules.confidence_scorer import CONFIDENCE_THRESHOLDS
from modules.strategy_mapper import NO_TRADE_CONDITIONS
import os; from dotenv import load_dotenv; load_dotenv()

checklist = []

# 1. Threshold restored
t = CONFIDENCE_THRESHOLDS['default']
checklist.append(('Confidence threshold = 52', t == 52))

# 2. NO_TRADE_CONDITIONS restored
checklist.append(('NO_TRADE_CONDITIONS restored', len(NO_TRADE_CONDITIONS) >= 5))

# 3. Backend running
try:
    r = requests.get('http://localhost:8000/api/live/status', timeout=2)
    checklist.append(('Backend API running', r.status_code == 200))
except:
    checklist.append(('Backend API running', False))

# 4. Env vars present
checklist.append(('ANGEL_API_KEY set', bool(os.getenv('ANGEL_API_KEY'))))
checklist.append(('MONGO_URL set', bool(os.getenv('MONGO_URL'))))
checklist.append(('TELEGRAM_BOT_TOKEN set', bool(os.getenv('TELEGRAM_BOT_TOKEN'))))

# 5. Log file writable
try:
    import os
    os.makedirs('logs', exist_ok=True)
    with open('logs/test_write.tmp','w') as f: f.write('test')
    os.remove('logs/test_write.tmp')
    checklist.append(('Log directory writable', True))
except:
    checklist.append(('Log directory writable', False))

print('TOMORROW READINESS CHECKLIST:')
print('=' * 45)
all_pass = True
for item, status in checklist:
    icon = '✅' if status else '❌'
    if not status: all_pass = False
    print(f'  {icon} {item}')
print('=' * 45)
print(f'RESULT: {"READY FOR TOMORROW" if all_pass else "FIX ISSUES ABOVE"}')
