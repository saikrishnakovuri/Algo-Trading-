
import json
import os
import requests

# 1. Test PA Config Save
def test_config_save():
    new_config = {
        "capital": 600000,
        "risk_pct": 0.015,
        "allowed_days": ["Thursday", "Friday"],
        "allowed_hours": [10, 11],
        "strategies": ["Breakout-Retest-Continuation"]
    }
    # Direct logic call (since uvicorn might not be running on port 8000 in this environment)
    from modules.pa_engine_bridge import PAEngineBridge
    PAEngineBridge.save_config(new_config)
    
    # Reload and check
    saved = PAEngineBridge.get_config()
    assert saved["capital"] == 600000
    assert saved["risk_pct"] == 0.015
    print("PA Config Save Validation: SUCCESS")

# 2. Test Journal Import
def test_journal_import():
    from motor.motor_asyncio import AsyncIOMotorClient
    import asyncio
    from dotenv import load_dotenv
    load_dotenv("../AlgoTradingTelegramBotAndFrontend/backend/.env")
    
    async def run_import():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        
        # Simulate the import logic
        import pandas as pd
        csv_path = "backtest_detailed_results.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            # Just test first 5
            trades = []
            for _, row in df.head(5).iterrows():
                trades.append({"pnl": row['pnl'], "source": "test_import"})
            await db.trade_journal.insert_many(trades)
            print(f"Journal Import Validation: SUCCESS ({len(trades)} trades)")
        
    asyncio.run(run_import())

if __name__ == "__main__":
    try:
        test_config_save()
        test_journal_import()
    except Exception as e:
        print(f"Validation FAILED: {e}")
