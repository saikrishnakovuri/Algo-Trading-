
import os
import re

TARGET_FILE = '../AlgoTradingTelegramBotAndFrontend/backend/server.py'

def fix_threading_issue():
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add MongoClient import at the top
    if 'from pymongo import MongoClient' not in content:
        content = content.replace(
            'from motor.motor_asyncio import AsyncIOMotorClient',
            'from motor.motor_asyncio import AsyncIOMotorClient\nfrom pymongo import MongoClient'
        )

    # 2. Define a sync db helper inside run_job or use a global one
    # Let's create a sync client near the async one
    if 'client_sync = MongoClient' not in content:
        content = content.replace(
            'db = client[os.environ["DB_NAME"]]',
            'db = client[os.environ["DB_NAME"]]\nclient_sync = MongoClient(mongo_url)\ndb_sync = client_sync[os.environ["DB_NAME"]]'
        )

    # 3. Replace asyncio.run(db...) with sync db_sync calls in run_job and grid_search
    # Pattern for run_job
    content = content.replace(
        'asyncio.run(db.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}}))',
        'db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}})'
    )
    content = content.replace(
        'asyncio.run(db.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "result": result, "completed_at": datetime.now(timezone.utc).isoformat(), "progress_pct": 100}}))',
        'db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "result": result, "completed_at": datetime.now(timezone.utc).isoformat(), "progress_pct": 100}})'
    )
    content = content.replace(
        'asyncio.run(db.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "FAILED", "error": str(e)}}))',
        'db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "FAILED", "error": str(e)}})'
    )

    # Do the same for grid-search if it exists (it was added in previous turns)
    # The grid_search block used similar logic
    content = content.replace(
        'asyncio.run(db.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}}))', # Duplicate catch
        'db_sync.backtest_jobs.update_one({"job_id": job_id}, {"$set": {"status": "RUNNING"}})'
    )
    
    # Write back
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Successfully converted async background jobs to thread-safe sync updates.")

if __name__ == "__main__":
    fix_threading_issue()
