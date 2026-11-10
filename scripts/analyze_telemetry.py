import re
import numpy as np

def run_telemetry_analysis():
    with open('data/post_17_1c_30d.txt', 'r', encoding='utf-16') as f:
        lines = f.readlines()

    bb_dist_upper = []
    bb_dist_lower = []
    vwap_dev = []
    rsi_vals = []

    for line in lines:
        m = re.search(r'MR_TELEM:BB .*dist_u_pct=(-?\d+\.\d+) dist_l_pct=(-?\d+\.\d+)', line)
        if m:
            bb_dist_upper.append(float(m.group(1)))
            bb_dist_lower.append(float(m.group(2)))
        m = re.search(r'MR_TELEM:VWAP .*dev_pct=(-?\d+\.\d+)', line)
        if m:
            vwap_dev.append(float(m.group(1)))
        m = re.search(r'MR_TELEM:RSI rsi=(-?\d+\.\d+)', line)
        if m:
            rsi_vals.append(float(m.group(1)))

    def pct(arr, label):
        if not arr:
            print(f"{label}: EMPTY")
            return
        a = np.array(arr)
        print(f"{label} n={len(a)} min={a.min():.3f} p05={np.percentile(a,5):.3f} p25={np.percentile(a,25):.3f} p50={np.percentile(a,50):.3f} p75={np.percentile(a,75):.3f} p90={np.percentile(a,90):.3f} p95={np.percentile(a,95):.3f} max={a.max():.3f}")

    print("=== MEAN_REVERSION TELEMETRY DISTRIBUTION ===")
    pct(bb_dist_upper, "BB dist_upper_pct")
    pct(bb_dist_lower, "BB dist_lower_pct")
    pct(vwap_dev,      "VWAP deviation %")
    pct(rsi_vals,      "RSI")

    # Top rejection reasons from the fail lines
    fail_counts = {}
    for line in lines:
        m = re.search(r'MR_TELEM:(\w+_FAIL)', line)
        if m:
            fail_counts[m.group(1)] = fail_counts.get(m.group(1), 0) + 1
    print("\n=== SUB-CHECK FAIL COUNTS ===")
    for k, v in sorted(fail_counts.items(), key=lambda x: -x[1]):
        print(f"  {v:>6}  {k}")

if __name__ == "__main__":
    run_telemetry_analysis()
