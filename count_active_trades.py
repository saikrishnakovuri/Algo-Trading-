import json

def count_active_trades(file_path):
    active_trades_count = 0
    try:
        with open(file_path, 'r') as f:
            trades = json.load(f)
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except json.JSONDecodeError:
        return f"Error: Could not decode JSON from {file_path}"

    for trade in trades:
        if trade.get('status') == 'OPEN':
            active_trades_count += 1
            
    return f"Number of active trades: {active_trades_count}"

if __name__ == "__main__":
    file_path = "c:\\Users\\91810\\OneDrive\\Desktop\\AlgoTrading Options\\data\\live_paper_trades.json"
    result = count_active_trades(file_path)
    print(result)
