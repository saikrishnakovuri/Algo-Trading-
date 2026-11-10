
import sys; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv()
import os
import requests
from pymongo import MongoClient

# TEST 1 — Angel One API
try:
    from SmartApi import SmartConnect
    import pyotp
    api = SmartConnect(api_key=os.getenv('ANGEL_API_KEY'))
    totp = pyotp.TOTP(os.getenv('ANGEL_TOTP_TOKEN')).now()
    data = api.generateSession(os.getenv('ANGEL_CLIENT_ID'), os.getenv('ANGEL_PIN'), totp)
    if data and data.get('status'):
        print(f'Angel One: CONNECTED | Token: {data["data"]["jwtToken"][:20]}...')
    else:
        print(f'Angel One: FAILED | Response: {data}')
except Exception as e:
    print(f'Angel One: FAILED | Error: {e}')

# TEST 2 — MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URL'), serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    db = client[os.getenv('DB_NAME')]
    collections = db.list_collection_names()
    print(f'MongoDB: CONNECTED | DB: {os.getenv("DB_NAME")} | Collections: {collections}')
except Exception as e:
    print(f'MongoDB: FAILED | {e}')

# TEST 3 — Telegram
try:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
        json={'chat_id': chat_id, 
              'text': '🔧 PRE-MARKET TEST: Bot diagnostic running. All systems check.'},
        timeout=5)
    if r.json().get('ok'):
        print(f'Telegram: SENT')
    else:
        print(f'Telegram: FAILED | {r.json()}')
except Exception as e:
    print(f'Telegram: FAILED | {e}')

# TEST 4 — Backend API
tests = [
    ('Live Status', 'http://localhost:8000/api/live/status'),
    ('Analytics Summary', 'http://localhost:8000/api/analytics/summary'),
    ('Settings', 'http://localhost:8000/api/settings'),
    ('Strategy Perf', 'http://localhost:8000/api/analytics/strategy-perf'),
    ('Live Context', 'http://localhost:8000/api/live/context'),
]
for name, url in tests:
    try:
        r = requests.get(url, timeout=3)
        print(f'{name}: {"OK" if r.status_code==200 else "FAILED"} | {r.status_code}')
    except Exception as e:
        print(f'{name}: OFFLINE')

# TEST 5 — Dashboard Frontend
try:
    r = requests.get('http://localhost:3000', timeout=3)
    print(f'Frontend: {"ONLINE" if r.status_code==200 else "FAILED"}')
except:
    print('Frontend: OFFLINE')
