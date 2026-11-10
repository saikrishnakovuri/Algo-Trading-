import pandas as pd
from datetime import time

WINNING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\winning09052026.xlsx"
LOSING_FILE = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\loosing09052026.xlsx"

# Load data
winning_df = pd.read_excel(WINNING_FILE, engine='openpyxl')
losing_df = pd.read_excel(LOSING_FILE, engine='openpyxl')

print("Sample of Entry_Time values from WINNING trades:")
print(winning_df['Entry_Time'].head(20))
print("\nData type:", winning_df['Entry_Time'].dtype)

print("\n" + "="*70)
print("\nSample of Entry_Time values from LOSING trades:")
print(losing_df['Entry_Time'].head(20))
print("\nData type:", losing_df['Entry_Time'].dtype)

# Try to parse
winning_df['entry_hour'] = pd.to_datetime(winning_df['Entry_Time'], errors='coerce').dt.hour
losing_df['entry_hour'] = pd.to_datetime(losing_df['Entry_Time'], errors='coerce').dt.hour

print("\n" + "="*70)
print("\nHour distribution WINNING trades:")
print(winning_df['entry_hour'].value_counts().sort_index())

print("\nHour distribution LOSING trades:")
print(losing_df['entry_hour'].value_counts().sort_index())

# Now look at actual times more carefully
print("\n" + "="*70)
print("\nMinute-level distribution for hour 9 (WINNING):")
winning_9 = winning_df[winning_df['entry_hour'] == 9]
winning_9['entry_minute'] = pd.to_datetime(winning_9['Entry_Time'], errors='coerce').dt.minute
print(winning_9['entry_minute'].value_counts().sort_index().head(20))

print("\nMinute-level distribution for hour 9 (LOSING):")
losing_9 = losing_df[losing_df['entry_hour'] == 9]
losing_9['entry_minute'] = pd.to_datetime(losing_9['Entry_Time'], errors='coerce').dt.minute
print(losing_9['entry_minute'].value_counts().sort_index().head(20))
