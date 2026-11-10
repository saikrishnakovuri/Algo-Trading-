from modules.broker_layer import AngelOneBroker
import pandas as pd
from datetime import datetime, timedelta

broker = AngelOneBroker()
broker.login()
# Correct format for Angel One: YYYY-MM-DD HH:MM
# Using a 1-day window to avoid the timedelta error
to_date = datetime.now()
from_date = to_date - timedelta(days=1)
from_str = from_date.strftime("%Y-%m-%d 09:15")
to_str = to_date.strftime("%Y-%m-%d 15:30")

df = broker.get_historical_data("NIFTY", "99926000", "FIVE_MINUTE", from_str, to_str)
if df is not None:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Current date in the DF
    today_str = to_date.strftime("%Y-%m-%d")
    df_today = df[df['timestamp'].dt.strftime('%Y-%m-%d') == today_str]
    df_window = df_today[(df_today['timestamp'] >= f'{today_str} 10:30:00') & (df_today['timestamp'] <= f'{today_str} 14:00:00')]
    print(df_window[['timestamp', 'open', 'high', 'low', 'close']])
else:
    print("Failed to fetch NIFTY data")
