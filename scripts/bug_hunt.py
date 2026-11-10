import os
import pandas as pd
import re

def bug_hunt():
    root = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options"
    source_files = []
    for dirpath, _, filenames in os.walk(root):
        if any(j in dirpath for j in ['venv', 'site-packages', 'Lib', '.git']): continue
        for f in filenames:
            if f.endswith('.py'):
                source_files.append(os.path.join(dirpath, f))

    patterns = {
        'NaN Propagation': r'[\+\-\*\/]\s*df\[', # Basic heuristic for math on columns
        'Division by Zero': r'\/.*(0|atr|std|range)',
        'Empty DataFrame Access': r'\.iloc\[-1\]',
        'Naive Datetime': r'datetime\.now\(\)',
        'Hardcoded Paths': r'[a-zA-Z]:\\',
    }

    report = "BUG_HUNT_REPORT.txt"
    with open(report, 'w', encoding='utf-8') as f:
        f.write("CODEBASE BUG HUNT REPORT\n========================\n\n")
        for pf in source_files:
            rel = os.path.relpath(pf, root)
            with open(pf, 'r', encoding='utf-8', errors='ignore') as src:
                content = src.read()
                file_bugs = []
                
                # Check for Empty DF guards
                if ".iloc[-1]" in content and "empty" not in content and "len(" not in content:
                    file_bugs.append("[RISK] .iloc[-1] without explicit empty/len check.")
                
                # Check for Division by Zero (loose)
                if "/" in content and "!= 0" not in content and "if" not in content:
                     # This is too noisy, but good to flag files for review
                     pass

                if file_bugs:
                    f.write(f"FILE: {rel}\n")
                    for b in file_bugs:
                        f.write(f"  - {b}\n")
                    f.write("\n")

    print(f"✅ Bug hunt complete. Report in {report}")

if __name__ == "__main__":
    bug_hunt()
