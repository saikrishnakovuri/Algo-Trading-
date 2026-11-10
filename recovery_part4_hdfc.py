import os
import pandas as pd
from backtest_engine import BacktestEngine

def run_hdfc_analysis():
    print("=== PART 4: HDFCBANK DEEP ANALYSIS ===")
    
    file_path = "data/extended/HDFCBANK_5m.csv"
    if not os.path.exists(file_path):
        print("HDFCBANK data missing.")
        return
        
    targets = [0.8, 1.0, 1.2, 1.5, 2.0]
    results = []
    
    print("\nRunning Tests on HDFCBANK...")
    for t in targets:
        print(f"\n--- Testing Target {t}R ---")
        engine = BacktestEngine(initial_capital=100000.0)
        engine.journal_file = f"temp_hdfc_{t}.csv"
        if os.path.exists(engine.journal_file):
            os.remove(engine.journal_file)
            
        trades = engine.run_massive_backtest_v2(
            files=[file_path],
            data_interval_minutes=5,
            step_size=1, # Since it's only 1 stock, step_size=1 is fast enough
            target_r_multiple=t,
            strategy_isolation_filter=None
        )
        
        perf = engine.calculate_performance(trades)
        perf['Target'] = f"{t}R"
        if perf["Total Trades"] > 0:
            win_rate = perf["Win Rate %"] / 100.0
            rr = perf["RR Ratio"]
            expectancy = (win_rate * rr) - (1 - win_rate)
        else:
            expectancy = 0
            
        perf['Expectancy(R)'] = round(expectancy, 3)
        results.append(perf)
        
    df_res = pd.DataFrame(results)
    cols = ['Target', 'Total Trades', 'Win Rate %', 'Expectancy(R)', 'Total Profit']
    df_out = df_res[cols]
    
    summary = "\nHDFCBANK DEEP ANALYSIS RESULTS\n"
    summary += "══════════════════════════════\n"
    summary += df_out.to_string(index=False)
    
    with open("recovery_results.md", "a", encoding="utf-8") as f:
        f.write("\n\n=== PART 4: HDFCBANK DEEP ANALYSIS ===\n")
        f.write(summary)
        
    print(summary)
    
if __name__ == "__main__":
    run_hdfc_analysis()