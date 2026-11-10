from modules.broker_layer import AngelOneBroker
import pandas as pd
from datetime import datetime

broker = AngelOneBroker()
broker.login()
# Fetch NIFTY (99926000) 5m bars for today
df = broker.get_historical_data("NIFTY", "99926000", "FIVE_MINUTE", "2026-05-25 09:15", "2026-05-25 15:30")
if df is not None:
    # Filter for the trade window 10:30 - 11:30
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_window = df[(df['timestamp'] >= '2026-05-25 10:30:00') & (df['timestamp'] <= '2026-05-25 12:00:00')]
    print(df_window[['timestamp', 'open', 'high', 'low', 'close']])
else:
    print("Failed to fetch NIFTY data")
