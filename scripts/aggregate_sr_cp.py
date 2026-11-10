import re
from collections import Counter

def aggregate_sr_cp():
    cp_totals = {}
    reject_counts = Counter()
    reject_samples = {}
    
    try:
        with open('data/post_17_2c_30d.txt', 'r', encoding='utf-16') as f:
            for line in f:
                # Aggregate CP counters
                m_cp = re.search(r'SR_CP symbol=\w+ (.+)', line)
                if m_cp:
                    for pair in m_cp.group(1).split():
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            if v.isdigit():
                                cp_totals[k] = cp_totals.get(k, 0) + int(v)
                
                # Capture rejection reasons
                m_rej = re.search(r'SR_REJECT:(\w+)', line)
                if m_rej:
                    key = m_rej.group(1)
                    reject_counts[key] += 1
                    if key not in reject_samples:
                        reject_samples[key] = line.strip()

        print("=== SWEEP_RETEST STATE MACHINE FUNNEL (30d) ===")
        for k in ['total_bars','sweep_detected','entered_awaiting_retest','retest_reached',
                 'confirmation_reached','signal_emitted','expired_no_retest','expired_no_confirm',
                 'rejected_wick_ratio','rejected_body_ratio','rejected_volume']:
            v = cp_totals.get(k, 0)
            print(f"  {k:35s}: {v}")

        print("\n=== REJECTION REASONS HISTOGRAM ===")
        for k, v in reject_counts.most_common():
            print(f"  {v:>6}  SR_REJECT:{k}")

        print("\n=== SAMPLE REJECTION LINES (one per reason) ===")
        for k, line in reject_samples.items():
            # Clean up line for report
            clean_line = line.split(']')[-1].strip() if ']' in line else line.strip()
            print(f"  {clean_line[:200]}")
            
    except Exception as e:
        print(f"Error during aggregation: {e}")

if __name__ == "__main__":
    aggregate_sr_cp()
