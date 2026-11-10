from modules.broker_layer import AngelOneBroker
import pandas as pd
from datetime import datetime

broker = AngelOneBroker()
broker.login()
df = broker.get_historical_data(
    symbol="NIFTY", 
    token="99926000", 
    interval="FIVE_MINUTE", 
    from_date_str="2026-05-25 13:30", 
    to_date_str="2026-05-25 15:30"
)

if df is not None:
    df.reset_index(inplace=True)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    print(df[['Timestamp', 'Open', 'High', 'Low', 'Close']])
else:
    print("Failed to fetch NIFTY data")
