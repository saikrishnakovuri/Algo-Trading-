import json
import pandas as pd
import os

def load_data():
    """Loads trade data from meta_db.json into a DataFrame."""
    if not os.path.exists("meta_db.json"):
        return pd.DataFrame()
        
    try:
        with open("meta_db.json", "r") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        return pd.DataFrame()
