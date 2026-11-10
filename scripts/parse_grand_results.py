import os
import re

log_dir = "logs/backtest_parts"
results = []

for filename in os.listdir(log_dir):
    if not filename.endswith(".log"):
        continue
    
    file_path = os.path.join(log_dir, filename)
    total_pnl = 0.0
    total_trades = 0
    wins = 0
    
    # Combination name from filename
    combo = filename.replace(".log", "")
    
    with open(file_path, "r") as f:
        for line in f:
            # Look for trade exit summaries
            if "Total Trade PnL=" in line or "Total PnL=" in line:
                match = re.search(r"Total (?:Trade )?PnL=([+-]?\d+\.?\d*)", line)
                if match:
                    pnl = float(match.group(1))
                    total_pnl += pnl
                    total_trades += 1
                    if pnl > 0:
                        wins += 1
            elif "INITIAL_SL_HIT" in line and "Total Trade PnL" not in line:
                # Some logs might have PnL on the same line but differently formatted
                match = re.search(r"PnL=([+-]?\d+\.?\d*)", line)
                if match:
                    pnl = float(match.group(1))
                    total_pnl += pnl
                    total_trades += 1
                    if pnl > 0:
                        wins += 1

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    results.append({
        "combo": combo,
        "pnl": total_pnl,
        "trades": total_trades,
        "win_rate": win_rate
    })

# Sort by PnL
results.sort(key=lambda x: x['pnl'], reverse=True)

print("| Combination | Total PnL (INR) | Trades | Win Rate |")
print("|-------------|-----------------|--------|----------|")
for r in results:
    print(f"| {r['combo']:35} | {r['pnl']:15,.2f} | {r['trades']:6} | {r['win_rate']:8.2f}% |")
