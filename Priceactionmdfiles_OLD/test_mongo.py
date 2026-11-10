
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv

load_dotenv("../AlgoTradingTelegramBotAndFrontend/backend/.env")

async def test_mongo():
    try:
        mongo_url = os.environ.get("MONGO_URL")
        print(f"Testing MongoDB connection to: {mongo_url}")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        print("MongoDB connection SUCCESSFUL!")
    except Exception as e:
        print(f"MongoDB connection FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_mongo())
