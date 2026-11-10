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
    
    combo = filename.replace(".log", "")
    
    with open(file_path, "r") as f:
        for line in f:
            # Only count final exit lines
            if "TSL SL EXIT:" in line or "TSL TRADE COMPLETE:" in line:
                match = re.search(r"Total (?:Trade )?PnL=([+-]?\d+\.?\d*)", line)
                if match:
                    pnl = float(match.group(1))
                    total_pnl += pnl
                    total_trades += 1
                    if pnl > 0:
                        wins += 1
                else:
                    # Fallback for INITIAL_SL_HIT which might not have "Total Trade PnL"
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

results.sort(key=lambda x: x['pnl'], reverse=True)

print("| Combination | Total PnL (INR) | Trades | Win Rate |")
print("|-------------|-----------------|--------|----------|")
for r in results:
    print(f"| {r['combo']:35} | {r['pnl']:15,.2f} | {r['trades']:6} | {r['win_rate']:8.2f}% |")
