import re
import numpy as np
from collections import Counter

def aggregate_ls_cp():
    ls_cp_totals = {}
    pools_above = []
    pools_below = []
    wick_ratios = []
    level_dev_pcts = []
    close_back_valid = Counter()
    
    try:
        with open('data/post_17_2c_30d.txt', 'r', encoding='utf-16') as f:
            for line in f:
                # Aggregate CP counters
                m_ls = re.search(r'LS_CP symbol=\? (.+)', line)
                if m_ls:
                    for pair in m_ls.group(1).split():
                        if '=' in pair:
                            k,v = pair.split('=',1)
                            if v.isdigit():
                                ls_cp_totals[k] = ls_cp_totals.get(k,0) + int(v)
                
                m_pool = re.search(r'LS_POOLS symbol=\? pools_above=(\d+) pools_below=(\d+)', line)
                if m_pool:
                    pools_above.append(int(m_pool.group(1)))
                    pools_below.append(int(m_pool.group(2)))
                
                m_wick = re.search(r'LS_TELEM:WICK .*ratio=([\d.]+)', line)
                if m_wick:
                    wick_ratios.append(float(m_wick.group(1)))
                    
                m_level = re.search(r'LS_TELEM:LEVEL .*dev_pct=([\d.]+)', line)
                if m_level:
                    level_dev_pcts.append(float(m_level.group(1)))
                
                m_close = re.search(r'LS_TELEM:CLOSE_BACK .*valid=(\w+)', line)
                if m_close:
                    close_back_valid[m_close.group(1)] += 1

        print("=== LIQUIDITY SWEEP DETECTOR FUNNEL ===")
        for k in ['bars_processed','has_liquidity_pool_above','has_liquidity_pool_below',
                 'swept_above_level','swept_below_level','passed_wick_ratio',
                 'failed_wick_ratio','passed_close_back_inside','failed_close_back_inside',
                 'emitted_sweep']:
            v = ls_cp_totals.get(k, 0)
            print(f"  {k:35s}: {v}")

        def pct(arr, label):
            if not arr:
                print(f"  {label:25s}: EMPTY")
                return
            a = np.array(arr)
            print(f"  {label:25s}: n={len(a):>5d}  min={a.min():.3f}  p25={np.percentile(a,25):.3f}  p50={np.percentile(a,50):.3f}  p75={np.percentile(a,75):.3f}  p90={np.percentile(a,90):.3f}  p95={np.percentile(a,95):.3f}  max={a.max():.3f}")

        print("\n=== LIQUIDITY POOL COUNTS (per call) ===")
        pct(pools_above, "pools_above")
        pct(pools_below, "pools_below")

        print("\n=== WICK/BODY RATIO DISTRIBUTION ===")
        pct(wick_ratios, "wick_ratio")

        print("\n=== LEVEL DEVIATION % (price vs nearest level) ===")
        pct(level_dev_pcts, "level_dev_pct")

        print(f"\n=== CLOSE-BACK VALID: {dict(close_back_valid)} ===")
            
    except Exception as e:
        print(f"Error during aggregation: {e}")

if __name__ == "__main__":
    aggregate_ls_cp()
