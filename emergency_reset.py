import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "tradealert_db")

client = MongoClient(mongo_url)
db = client[db_name]

# 1. Clear fake active positions from live_state
res1 = db.live_state.update_one({}, 
    {"$set": {"active_positions": [], 
              "daily_pnl": 0.0}})
print(f"live_state updated: {res1.modified_count} docs")

# 2. Clear fake trades if any (those without a strategy or with massive negative PnL)
res2 = db.bot_trades.delete_many({"net_pnl": {"$lt": -50000}})
print(f"bot_trades cleaned: {res2.deleted_count} docs")

print("Fake positions and PnL reset complete.")
client.close()
