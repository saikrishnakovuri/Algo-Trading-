
import os

TARGET_FILE = '../backtest_engine.py'

def final_surgical_repair():
    if not os.path.exists(TARGET_FILE):
        print(f"Error: {TARGET_FILE} not found")
        return

    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    keyword = 'return all_trades'
    idx = content.find(keyword)
    
    if idx == -1:
        print("Could not find anchor 'return all_trades'. Repair aborted.")
        return

    end_of_method = content.find('\n', idx)
    if end_of_method == -1: end_of_method = len(content)
    
    clean_base = content[:end_of_method].strip()
    
    NEW_FUNCTIONS = """

def run(config):
    \"\"\"Standalone entry point for backend server. Matches frontend expected schema.\"\"\"
    engine = BacktestEngine(initial_capital=float(config.get("capital", 1000000)))
    
    # Resolve files
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nifty200")
    
    files = []
    stocks = config.get("stocks", ["NIFTY"])
    for s in stocks:
        fpath = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(fpath):
            files.append(fpath)
            
    if not files:
        print(f"Warning: No data files found in {data_dir} for stocks {stocks}")
        
    raw_trades = engine.run_massive_backtest_v2(
        files=files,
        start_date=config.get("start_date"),
        end_date=config.get("end_date"),
        strategy_isolation_filter=config.get("entry_strategy")
    )
    
    # Transform trades to match frontend expectations
    # Frontend expects: net_pnl, entry_price, exit_price, entry_time
    formatted_trades = []
    for t in raw_trades:
        formatted_trades.append({
            **t,
            "net_pnl": t.get("pnl", 0),
            "entry_price": t.get("entry", 0),
            "exit_price": t.get("entry", 0) + (t.get("pnl", 0) / t.get("qty", 1)) if t.get("qty", 0) > 0 else t.get("entry", 0),
            "entry_time": t.get("date", ""),
        })
    
    stats = engine.calculate_performance(raw_trades)
    
    # Transform stats to match frontend 'metrics' field
    return {
        "metrics": {
            "total_trades": stats.get("total_trades", 0),
            "win_rate": stats.get("win_rate", 0),
            "total_pnl": stats.get("total_pnl", 0),
            "profit_factor": stats.get("profit_factor", 0),
        },
        "trades": formatted_trades
    }

def grid_search(config):
    \"\"\"Stub for grid search functionality.\"\"\"
    return {"status": "error", "message": "Grid search not implemented in this engine version"}
"""
    
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(clean_base)
        f.write(NEW_FUNCTIONS)
        
    print("Final schema-aligned repair of backtest_engine.py COMPLETE.")

if __name__ == "__main__":
    final_surgical_repair()
