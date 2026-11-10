import subprocess
import os

def run_backtest(target, symbols):
    print(f"--- Running Baseline Backtest: Target {target}R ---")
    subprocess.run(["python", "baseline_setup.py", "target", str(target)])
    
    cmd = [
        "python", "run_backtest.py",
        "--symbols"
    ] + symbols + [
        "--days", "180"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Print the output to the main log so we can see it
    print(result.stdout)
    return result.stdout

def main():
    symbols = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", 
        "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"
    ]
    
    results = {}
    for target in [1.0, 1.5, 2.0]:
        output = run_backtest(target, symbols)
        # Parse output for stats
        # UNIFIED BACKTEST RESULTS
        # Total Trades        : X
        # Win Rate %          : X
        # RR Ratio            : X
        # Total Profit        : X
        
        stats = {}
        for line in output.split('\n'):
            if ':' in line:
                parts = line.split(':')
                key = parts[0].strip()
                val = parts[1].strip()
                if key in ["Total Trades", "Win Rate %", "RR Ratio", "Total Profit"]:
                    stats[key] = val
        results[target] = stats
        print(f"Target {target}R: {stats}")

    # Report
    table = "\n### PART 2: RAW BASELINE\n"
    table += "| Target | Trades | Win% | RR | Expect(R) | P&L |\n"
    table += "|---|---|---|---|---|---|\n"
    for target, stats in results.items():
        win_rate = float(stats.get('Win Rate %', 0)) / 100
        rr = float(stats.get('RR Ratio', 0))
        # Expectancy = (Win% * target) - (Loss% * 1.0)
        # Note: In our system RR Ratio is avg_win / avg_loss. 
        # For simplicity in this baseline table, I'll use the target R as the win value if RR is consistent.
        # But better to use the calculated stats.
        expectancy = round((win_rate * rr) - ((1 - win_rate) * 1.0), 3)
        
        table += f"| {target}R | {stats.get('Total Trades')} | {stats.get('Win Rate %')}% | {stats.get('RR Ratio')} | {expectancy} | {stats.get('Total Profit')} |\n"

    with open("optimization_results.md", "a") as f:
        f.write(table)
    print(table)

if __name__ == "__main__":
    main()
