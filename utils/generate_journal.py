import pandas as pd
import os
from datetime import datetime
import xlsxwriter

def generate_daily_journal():
    # Load all trades from MongoDB or local storage (if available)
    # Assuming the existence of a 'trades' collection or a daily jsonl log
    # For this implementation, we read from the database
    from pymongo import MongoClient
    
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "tradealert_db")
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    # Get today's trades
    today_str = datetime.now().strftime("%Y-%m-%d")
    trades = list(db.trades.find({"entry_time": {"$regex": today_str}}, {"_id": 0}))
    
    if not trades:
        print("No trades found for today. Skipping Excel generation.")
        return

    # Calculate P&L metrics
    total_pnl = sum([t.get("pnl", 0) for t in trades if t.get("status") == "CLOSED"])
    
    # Export to Excel
    filename = f"Journal_{datetime.now().strftime('%Y%m%d')}.xlsx"
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    
    df = pd.DataFrame(trades)
    df.to_excel(writer, sheet_name='Trades', index=False)
    
    # Add Summary Sheet
    summary_data = {
        "Metric": ["Total Trades", "Realized P&L", "Win Rate"],
        "Value": [
            len(trades),
            total_pnl,
            f"{(len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) * 100):.1f}%" if trades else "0%"
        ]
    }
    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
    
    writer.close()
    print(f"Journal saved as {filename}")

if __name__ == "__main__":
    generate_daily_journal()
