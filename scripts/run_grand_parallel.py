import subprocess
import os
import glob
import time

sl_modes = ["FLAT_1PCT", "SECTOR_REALISTIC", "RR_2_1", "ZONE"]
target_modes = ["SECTOR_GRADUATED", "PRICE_LADDER_25_75", "ATR_REALISTIC"]

os.makedirs("logs/backtest_parts", exist_ok=True)

processes = []
for sm in sl_modes:
    for tm in target_modes:
        print(f"🚀 Starting backtest for {sm} x {tm}...")
        log_file = f"logs/backtest_parts/{sm}_{tm}.log"
        with open(log_file, "w") as f:
            # We use subprocess.Popen to run in parallel
            p = subprocess.Popen(
                ["python", "scripts/test_50_stocks_3_months.py", "--sl_mode", sm, "--target_mode", tm],
                stdout=f,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONPATH": "."}
            )
            processes.append((p, sm, tm, log_file))
        
        # Stagger starts to avoid disk IO bottleneck
        time.sleep(2)

print(f"\n⏳ All {len(processes)} combinations started. Waiting for completion...")

results = {}
while processes:
    for i in range(len(processes)-1, -1, -1):
        p, sm, tm, log_file = processes[i]
        if p.poll() is not None:
            # Process finished
            print(f"✅ Finished: {sm} x {tm}")
            # Extract final result from log
            with open(log_file, "r") as lf:
                lines = lf.readlines()
                for line in reversed(lines):
                    if "FINAL_RESULT|" in line:
                        parts = line.strip().split("|")
                        results[parts[1]] = float(parts[2])
                        break
            processes.pop(i)
    time.sleep(10)

print("\n" + "="*60)
print("GRAND BACKTEST RESULTS (SUMMARY)")
print("="*60)
for combo in sorted(results, key=results.get, reverse=True):
    print(f"{combo:35}: {results[combo]:>15,.2f} INR")
print("="*60)
