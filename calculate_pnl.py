import json
from datetime import datetime

def calculate_daily_pnl(file_path, target_date_str):
    total_pnl = 0.0
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

    try:
        with open(file_path, 'r') as f:
            trades = json.load(f)
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except json.JSONDecodeError:
        return f"Error: Could not decode JSON from {file_path}"

    for trade in trades:
        opened_at_str = trade.get('opened_at')
        closed_at_str = trade.get('closed_at')
        pnl = trade.get('pnl', 0.0)

        # Check if the trade was opened or closed on the target date
        trade_date_match = False
        if opened_at_str:
            opened_date = datetime.fromisoformat(opened_at_str).date()
            if opened_date == target_date:
                trade_date_match = True
        
        # If not opened today, check if closed today. This avoids double counting if opened and closed on the same day.
        if not trade_date_match and closed_at_str:
            closed_date = datetime.fromisoformat(closed_at_str).date()
            if closed_date == target_date:
                trade_date_match = True

        if trade_date_match:
            total_pnl += pnl

    return f"Total P&L for {target_date_str}: {total_pnl:.2f}"

if __name__ == "__main__":
    file_path = "c:\\Users\\91810\\OneDrive\\Desktop\\AlgoTrading Options\\data\\live_paper_trades.json"
    today_date = "2026-05-20"
    result = calculate_daily_pnl(file_path, today_date)
    print(result)
