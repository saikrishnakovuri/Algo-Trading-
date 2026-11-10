
import sys; sys.path.insert(0,'.')
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
try:
    client = MongoClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME')]

    # Today's trades
    trades = list(db.bot_trades.find({'mode':'PAPER'}).sort('entry_time',-1).limit(20))
    print(f'Paper trades today: {len(trades)}')
    for t in trades:
        print(f'  {t.get("trade_id")} | {t.get("symbol")} {t.get("direction")} | PnL: {t.get("net_pnl","OPEN")}')

    # Today's signals
    signals = list(db.bot_events.find({'event_type':'SIGNAL'}).sort('timestamp',-1).limit(10))
    print(f'Signals generated: {len(signals)}')

    # Errors in events
    errors = list(db.bot_events.find({'level':'ERROR'}).sort('timestamp',-1).limit(5))
    print(f'Errors logged: {len(errors)}')
except Exception as e:
    print(f'Audit Session Failed: {e}')
