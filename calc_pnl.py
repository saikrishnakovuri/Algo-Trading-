from modules.broker_layer import AngelOneBroker
import pandas as pd

broker = AngelOneBroker()
broker.login()

# Fetch today's 5m data
df = broker.get_historical_data(
    symbol="NIFTY", 
    token="99926000", 
    interval="FIVE_MINUTE", 
    from_date_str="2026-05-25 09:15", 
    to_date_str="2026-05-25 15:30"
)

if df is not None:
    df.reset_index(inplace=True)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # 1. Trade 1: 09:55 AM
    entry_1 = df[df['Timestamp'] == '2026-05-25 09:55:00+05:30']['Close'].iloc[0]
    # Check max high after 09:55
    max_high_1 = df[df['Timestamp'] > '2026-05-25 09:55:00+05:30']['High'].max()
    
    # 2. Trade 2: 10:30 AM
    entry_2 = df[df['Timestamp'] == '2026-05-25 10:30:00+05:30']['Close'].iloc[0]
    # Check max high after 10:30
    max_high_2 = df[df['Timestamp'] > '2026-05-25 10:30:00+05:30']['High'].max()
    
    close_price = df.iloc[-1]['Close']
    
    print(f"Trade 1 (09:55): Entry {entry_1:.2f} | Max High {max_high_1:.2f} | Close {close_price:.2f}")
    print(f"Trade 2 (10:30): Entry {entry_2:.2f} | Max High {max_high_2:.2f} | Close {close_price:.2f}")
