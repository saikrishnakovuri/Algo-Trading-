import json
import datetime
from pathlib import Path

def force_close_all():
    path = Path("data/live_paper_trades.json")
    if not path.exists():
        print("No trade file found.")
        return

    trades = json.loads(path.read_text(encoding="utf-8"))
    closed_ids = {t["trade_id"] for t in trades if t["status"] == "CLOSED"}
    
    new_events = []
    closed_count = 0
    
    for t in trades:
        new_events.append(t)
        if t["status"] == "OPEN" and t["trade_id"] not in closed_ids:
            # Create a closure event
            close_evt = t.copy()
            close_evt["status"] = "CLOSED"
            close_evt["exit_price"] = t["entry_price"]
            close_evt["exit_reason"] = "FORCE_CLOSE"
            close_evt["closed_at"] = datetime.datetime.now().isoformat()
            close_evt["pnl"] = 0.0
            new_events.append(close_evt)
            # Add to closed_ids to avoid duplicate closure events if multiple OPEN entries exist
            closed_ids.add(t["trade_id"])
            closed_count += 1
            
    path.write_text(json.dumps(new_events, indent=2), encoding="utf-8")
    print(f"✅ Force closed {closed_count} unclosed positions.")

if __name__ == "__main__":
    force_close_all()
