
import os

TARGET_FILE = '../backtest_engine.py'

def fix_backtest_engine():
    if not os.path.exists(TARGET_FILE):
        print(f"Error: {TARGET_FILE} not found")
        return

    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find where the broken part starts. It started after "return all_trades"
    clean_lines = []
    found_broken = False
    for line in lines:
        if 'def run(config):' in line and '\\"' in line:
            found_broken = True
            break
        if not found_broken:
            clean_lines.append(line)

    # If we didn't find the exact 'def run' line, let's look for any line with backslashes that shouldn't be there
    # Actually, let's just truncate from the first occurrence of the corrupted 'def run'
    
    final_content = "".join(clean_lines).strip()
    
    # Append the correct implementation
    CORRECT_APPEND = """

def run(config):
    \"\"\"Standalone entry point for backend server.\"\"\"
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
        
    trades = engine.run_massive_backtest_v2(
        files=files,
        start_date=config.get("start_date"),
        end_date=config.get("end_date"),
        strategy_isolation_filter=config.get("entry_strategy")
    )
    
    stats = engine.calculate_performance(trades)
    return {
        "summary": stats,
        "trades": trades
    }

def grid_search(config):
    \"\"\"Stub for grid search functionality.\"\"\"
    return {"status": "error", "message": "Grid search not implemented in this engine version"}
"""
    
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)
        f.write(CORRECT_APPEND)
    
    print("Successfully fixed backtest_engine.py syntax errors.")

if __name__ == "__main__":
    fix_backtest_engine()
