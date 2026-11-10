import os
import json
from backtest_engine import BacktestEngine
from meta_learning.analyzer import analyze
from meta_learning.filter_engine import filter_entities
from meta_learning.config_updater import update_config

def run_evolution():
    print("🚀 PHASE 1: Running Massive Backtest to collect data...")
    data_dir = "data/nifty200"
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith("_1m.csv")]
    
    # Initialize Engine
    engine = BacktestEngine(initial_capital=100000.0)
    
    # Persistent Meta-Learning: We no longer delete meta_db.json to build statistical significance.
    # if os.path.exists("meta_db.json"):
    #     os.remove("meta_db.json")
    
    trades = engine.run_massive_backtest_v2(all_files)
    
    if not trades:
        print("❌ No trades to learn from. Evolution halted.")
        return

    print("\n🧠 PHASE 2: Analyzing trade data for Edge...")
    with open("meta_db.json", "r") as f:
        db_trades = json.load(f)
    
    stats = analyze(db_trades)
    
    print("\n⚖️ PHASE 3: Filtering profitable entities...")
    allowed_stocks, allowed_setups = filter_entities(stats)
    
    print(f"Top 5 Stocks Identified: {allowed_stocks[:5]}")
    print(f"Setups to Keep: {allowed_setups}")

    print("\n🔄 PHASE 4: Updating system configuration...")
    update_config(allowed_stocks, allowed_setups)
    
    print("\n✨ EVOLUTION COMPLETE: System is now optimized for the best stocks and setups.")

if __name__ == "__main__":
    run_evolution()
