import re
import numpy as np
from collections import Counter

def run_analysis():
    for fname, tag in [('data/post_17_2e_30d.txt','30d'), ('data/post_17_2e_60d.txt','60d')]:
        depths, wicks = [], []
        r = Counter()
        try:
            with open(fname, 'r', encoding='utf-16') as f:
                for line in f:
                    m = re.search(r'SRD:DEPTH:([\d.]+)', line)
                    if m: depths.append(float(m.group(1)))
                    m = re.search(r'SRD:WICK:([\d.]+)', line)
                    if m: wicks.append(float(m.group(1)))
                    m = re.search(r'SRD:REJECT:(\w+)', line)
                    if m: r[m.group(1)] += 1

            def pct(a, lbl):
                if not a: 
                    print(f"  {lbl}: EMPTY")
                    return
                a = np.array(a)
                print(f"  {lbl} n={len(a)} min={a.min():.3f} p25={np.percentile(a,25):.3f} p50={np.percentile(a,50):.3f} p75={np.percentile(a,75):.3f} p90={np.percentile(a,90):.3f} max={a.max():.3f}")

            print(f"\n=== SWEEP_RETEST DIAG [{tag}] ===")
            pct(depths, 'depth_pct')
            pct(wicks, 'wick_ratio')
            print(f"  rejections: {dict(r)}")
        except Exception as e:
            print(f"Error reading {fname}: {e}")

if __name__ == "__main__":
    run_analysis()
