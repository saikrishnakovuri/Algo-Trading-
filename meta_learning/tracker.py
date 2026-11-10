import json
import os

DB_FILE = "meta_db.json"

def log_trade(trade):
    """Saves detailed trade data to meta_db.json for analyzer."""
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []

    data.append(trade)

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)
