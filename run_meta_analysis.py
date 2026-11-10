import pandas as pd
import numpy as np

from meta_learning.analyzer import analyze, compute_metrics

def analyze_meta():
    try:
        import os
        import glob
        # Find the latest meta_db file
        files = glob.glob("meta_db_*.json")
        if not files:
            print("No meta database found. Run a backtest first.")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        print(f"📖 Analyzing latest session: {latest_file}")
        
        import json
        with open(latest_file, "r") as f:
            db_trades = json.load(f)
    except Exception as e:
        print(f"Error reading meta_db.json: {e}")
        return

    if not db_trades:
        print("Journal is empty. Run a backtest first.")
        return

    stats = analyze(db_trades)

    print("\n" + "="*50)
    print("🧠 ELITE META-LEARNING ANALYSIS (V3 EDGE)")
    print("="*50)
    
    # 1. Performance by Stock (Elite Filtering)
    stock_report = []
    for stock, pnls in stats["by_stock"].items():
        m = compute_metrics(pnls)
        stock_report.append({
            "Symbol": stock,
            "PnL": round(sum(pnls), 2),
            "Trades": m["trades"],
            "WinRate": f"{m['win_rate']}%",
            "Consistency": f"{m['consistency']*100:.0f}%",
            "Expectancy": m["expectancy"]
        })
    
    df_stocks = pd.DataFrame(stock_report).sort_values(by="PnL", ascending=False)
    
    print("\n🏆 TOP 10 PROFITABLE STOCKS:")
    print(df_stocks.head(10).to_string(index=False))

    print("\n🚫 BOTTOM 10 STOCKS (KILL LIST):")
    print(df_stocks.tail(10).to_string(index=False))

    # 2. Performance by Time Window (Split Window Check)
    print("\n⏰ TIME-WINDOW EDGE ANALYSIS:")
    for window, pnls in stats["by_time_window"].items():
        m = compute_metrics(pnls)
        print(f"- {window:35} | PnL: ₹{sum(pnls):8.2f} | Trades: {len(pnls):3} | Win%: {m['win_rate']}%")

    # 3. Setup Performance
    print("\n🎯 SETUP CONVICTION ANALYSIS:")
    for setup, pnls in stats["by_setup"].items():
        m = compute_metrics(pnls)
        print(f"- {setup:20} | PnL: ₹{sum(pnls):8.2f} | Trades: {len(pnls):3} | Expectancy: {m['expectancy']}")

    # 4. Whitelist Generation (Top 30% with > 5 trades)
    eligible = df_stocks[df_stocks["Trades"] >= 5]
    keep_count = max(1, int(len(eligible) * 0.3))
    whitelist = eligible.head(keep_count)["Symbol"].tolist()
    
    print("\n✨ RECOMMENDED ELITE WHITELIST (Top 30%):")
    print(whitelist)

    print("\n" + "="*50)
    
    # Save to CSV
    df_stocks.to_csv("meta_stock_stats.csv", index=False)
    print("📝 Full report saved to meta_stock_stats.csv")

if __name__ == "__main__":
    import pandas as pd
    analyze_meta()
