import os
import glob
import pandas as pd
from backtest_engine import BacktestEngine

def run_baseline():
    print("=== PART 3: LARGE-SAMPLE BASELINE (5m Data) ===")
    
    stocks = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "INFY"
    ]
    
    files = []
    for s in stocks:
        fp = f"data/extended/{s}_5m.csv"
        if os.path.exists(fp):
            files.append(fp)
            
    print(f"Found {len(files)} 5m files for baseline test.")
    
    targets = [1.0, 1.5, 2.0]
    results = []
    
    for t in targets:
        print(f"\n--- Testing Target {t}R ---")
        engine = BacktestEngine(initial_capital=100000.0)
        # Clear journal file if needed
        engine.journal_file = f"temp_journal_{t}.csv"
        if os.path.exists(engine.journal_file):
            os.remove(engine.journal_file)
            
        trades = engine.run_massive_backtest_v2(
            files=files,
            data_interval_minutes=5,
            step_size=2, # step 2 bars of 5m to speed up
            target_r_multiple=t,
            strategy_isolation_filter=None # No strategy filters to test baseline
        )
        
        perf = engine.calculate_performance(trades)
        perf['Target'] = f"{t}R"
        
        # Calculate Expectancy (R)
        if perf["Total Trades"] > 0:
            win_rate = perf["Win Rate %"] / 100.0
            rr = perf["RR Ratio"]
            expectancy = (win_rate * rr) - (1 - win_rate)
        else:
            expectancy = 0
            
        perf['Expectancy(R)'] = round(expectancy, 3)
        results.append(perf)
        
    df_res = pd.DataFrame(results)
    
    cols = ['Target', 'Total Trades', 'Win Rate %', 'RR Ratio', 'Expectancy(R)', 'Total Profit']
    df_out = df_res[cols]
    
    summary = "\nLARGE-SAMPLE BASELINE RESULTS\n"
    summary += "═════════════════════════════\n"
    summary += df_out.to_string(index=False)
    
    with open("recovery_results.md", "a", encoding="utf-8") as f:
        f.write("\n\n=== PART 3: LARGE-SAMPLE BASELINE (5m Data) ===\n")
        f.write(summary)
        
    print(summary)
    
    # Check decision
    best_expectancy = df_out['Expectancy(R)'].max()
    max_trades = df_out['Total Trades'].max()
    
    if best_expectancy > 0 and max_trades >= 50:
        decision = "DECISION: PROCEED to Option A and C (Parts 4-9)"
    else:
        decision = "DECISION: FUNDAMENTAL_REWORK_NEEDED (Edge not verified on 50+ trades)"
        
    print(f"\n{decision}")
    with open("recovery_results.md", "a", encoding="utf-8") as f:
        f.write(f"\n\n{decision}\n")

if __name__ == "__main__":
    run_baseline()