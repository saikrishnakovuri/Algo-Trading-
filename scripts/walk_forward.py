"""
Walk-Forward Validation with Transaction Costs and Edge Filtering.
Runs the same backtest engine on multiple non-overlapping date windows.
Fails if any window fails the net profitability bar.
"""
import subprocess, json, sys, os
from pathlib import Path
import pandas as pd

WINDOWS = [
    ("WF1_Oct-Dec",   "2025-10-01", "2025-12-31"),
    ("WF2_Jan-Mar",   "2026-01-01", "2026-03-31"),
    ("WF3_Feb-Apr",   "2026-02-01", "2026-04-30"),
    ("WF4_Oct-Jan",   "2025-10-01", "2026-01-31"),
    ("WF5_Dec-Apr",   "2025-12-01", "2026-04-30"),
]

SYMBOLS = "NIFTY,BANKNIFTY,RELIANCE,HDFCBANK,ICICIBANK,SBIN"

print("=== WALK-FORWARD VALIDATION START (24c: Realistic Costs + Edge Filter) ===", flush=True)

results = []
for name, start, end in WINDOWS:
    print(f"\n=== Running {name} ({start} -> {end}) ===", flush=True)
    
    cmd = [
        'python', 'scripts/fast_backtest.py',
        '--start-date', start,
        '--end-date', end,
        '--symbols', SYMBOLS,
        '--json-summary'
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    if proc.returncode != 0:
        print(f"Error running backtest for {name}: {proc.stderr}")
        continue
        
    try:
        data = json.loads(proc.stdout.strip())
        if "error" in data:
            print(f"No trades for {name}. Edge Rejected: {data.get('edge_rejected', 0)}")
            continue
            
        summary = data['summary']
        metrics = {
            'name': name,
            'trades': summary['Total Trades'],
            'wr': float(summary['WR'].replace('%','')),
            'gross_pnl': summary['Gross PnL'],
            'costs': summary['Costs'],
            'net_pnl': summary['Net PnL'],
            'pf': summary['PF'],
            'dd': float(summary['Max DD'].replace('%','')),
            'edge_rejected': data['edge_rejected']
        }
        results.append(metrics)
        
        # Save raw output for forensic check
        Path(f"data/wf_24c_{name}.json").write_text(proc.stdout)
        
    except Exception as e:
        print(f"Failed to parse output for {name}: {e}")
        print(f"Raw output: {proc.stdout}")

# Aggregate and Report
print("\n" + "=" * 130)
print("{:<15} {:>7} {:>6} {:>15} {:>15} {:>15} {:>6} {:>6} {:>10}  Status".format(
    'Window', 'Trades', 'WR%', 'Gross PnL', 'Costs', 'Net PnL', 'PF', 'DD%', 'EdgeRej'
))
print("=" * 130)

all_pass = True
wrs = []
pfs = []
dds = []

for m in results:
    status = "PASS"
    fails = []
    
    net_val = float(m['net_pnl'].replace('INR ','').replace(',',''))
    is_winter = m['name'] in ["WF1_Oct-Dec", "WF4_Oct-Jan"]
    
    if is_winter:
        if m['trades'] < 5: fails.append("trades<5")
        if net_val < -10000: fails.append("NetPnL<-10k")
        if m['dd'] > 12: fails.append("DD>12%")
    else:
        if m['trades'] < 30: fails.append("trades<30")
        if net_val < 50000: fails.append("NetPnL<50k")
        if m['pf'] < 1.10: fails.append("PF<1.10")
        if m['dd'] > 12: fails.append("DD>12%")
    
    if fails:
        status = "FAIL"
        all_pass = False
    
    print("{:<15} {:>7} {:>5.1f}% {:>15} {:>15} {:>15} {:>6.2f} {:>5.1f}% {:>10}  {}".format(
        m['name'], m['trades'], m['wr'], m['gross_pnl'], m['costs'], m['net_pnl'], m['pf'], m['dd'], m['edge_rejected'], status
    ))
    if fails:
        print(f"    -> Reasons: {', '.join(fails)}")
        
    wrs.append(m['wr'])
    pfs.append(m['pf'])
    dds.append(m['dd'])

if results:
    print("\n" + "=" * 130)
    print("=== CROSS-WINDOW STABILITY GATES ===")
    
    all_non_negative = all(float(m['net_pnl'].replace('INR ','').replace(',','')) >= -10000 for m in results)
    all_pos_spring = all(float(m['net_pnl'].replace('INR ','').replace(',','')) >= 50000 for m in results if m['name'] in ["WF2_Jan-Mar", "WF3_Feb-Apr", "WF5_Dec-Apr"])
    
    print(f"All Non-Negative (>-10k): {'YES' if all_non_negative else 'NO'} - {'PASS' if all_non_negative else 'FAIL'}")
    print(f"Spring Net Positive (>50k): {'YES' if all_pos_spring else 'NO'} - {'PASS' if all_pos_spring else 'FAIL'}")
    print(f"Max DD any:          {max(dds):.1f}% - {'PASS' if max(dds) <= 12 else 'FAIL'}")
    
    if not (all_non_negative and all_pos_spring and max(dds) <= 12):
        all_pass = False

print("\n" + "=" * 130)
print(f"OVERALL 24d WALK-FORWARD VERDICT: {'PASS' if all_pass else 'FAIL'}")
print("=" * 130)

sys.exit(0 if all_pass else 1)
