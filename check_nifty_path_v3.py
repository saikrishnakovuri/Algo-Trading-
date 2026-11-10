from modules.broker_layer import AngelOneBroker
import pandas as pd
from datetime import datetime

broker = AngelOneBroker()
broker.login()
# Use NAMED arguments to avoid positional mismatch with 'days'
df = broker.get_historical_data(
    symbol="NIFTY", 
    token="99926000", 
    interval="FIVE_MINUTE", 
    from_date_str="2026-05-25 09:15", 
    to_date_str="2026-05-25 15:30"
)

if df is not None:
    df.reset_index(inplace=True)
    # Filter for the trade window 10:30 onwards
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df_window = df[df['Timestamp'] >= '2026-05-25 10:30:00']
    print(df_window[['Timestamp', 'Open', 'High', 'Low', 'Close']])
else:
    print("Failed to fetch NIFTY data")
