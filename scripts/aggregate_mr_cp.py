import re

def aggregate_mr_cp():
    totals = {'total':0,'pass_antitrend':0,'reached_subchecks':0,'had_signals':0,'passed_score':0,'returned':0}
    try:
        with open('data/post_17_1g_30d.txt', 'r', encoding='utf-16') as f:
            for line in f:
                m = re.search(r'MR_CP .*total=(\d+) pass_antitrend=(\d+) reached_subchecks=(\d+) had_signals=(\d+) passed_score=(\d+) returned=(\d+)', line)
                if m:
                    totals['total']           += int(m.group(1))
                    totals['pass_antitrend']  += int(m.group(2))
                    totals['reached_subchecks'] += int(m.group(3))
                    totals['had_signals']      += int(m.group(4))
                    totals['passed_score']     += int(m.group(5))
                    totals['returned']         += int(m.group(6))
                    
        print("=== MR FUNNEL (30d, anti-trend OFF, thresholds LOOSENED) ===")
        print(f"  total bars examined:       {totals['total']}")
        div = max(1, totals['total'])
        print(f"  passed anti-trend filter:  {totals['pass_antitrend']}  ({100*totals['pass_antitrend']/div:.1f}%)")
        print(f"  reached sub-checks:        {totals['reached_subchecks']}")
        print(f"  had signals fired:         {totals['had_signals']}  ← KEY")
        print(f"  passed min_score:          {totals['passed_score']}")
        print(f"  returned signal:           {totals['returned']}")
    except Exception as e:
        print(f"Error during aggregation: {e}")

if __name__ == "__main__":
    aggregate_mr_cp()
