import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URL"))
db = client[os.getenv("DB_NAME", "tradealert_db")]

res = db.bot_commands.update_many({}, {"$set": {"status": "PENDING"}})
print(f"Reset {res.modified_count} commands to PENDING")
client.close()
