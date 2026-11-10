import sqlite3
import pandas as pd
from datetime import datetime

def check_trades():
    conn = sqlite3.connect('trades.db')
    # ts is TEXT, we'll search for today's date in it.
    query = "SELECT * FROM trades WHERE ts LIKE '2026-05-20%'"
    try:
        df = pd.read_sql_query(query, conn)
        print("--- Today's Trades (2026-05-20) in trades.db ---")
        if df.empty:
            print("No trades found for today in trades.db.")
        else:
            print(df)
    except Exception as e:
        print(f"Error reading trades.db: {e}")
    finally:
        conn.close()

    # Also check the trade_journal.csv
    try:
        df_journal = pd.read_csv('trade_journal.csv')
        # date column exists
        today_journal = df_journal[df_journal['date'] == '2026-05-20']
        print("\n--- Today's Journal Entries ---")
        if today_journal.empty:
            # Maybe date format is different? Check head.
            print("No journal entries found for 2026-05-20. Checking recent entries...")
            print(df_journal.tail(5))
        else:
            print(today_journal)
    except Exception as e:
        print(f"Error reading trade_journal.csv: {e}")

if __name__ == "__main__":
    check_trades()
