import os
import subprocess
import sys

def run_command(command: str):
    print(f"Executing: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in process.stdout:
        print(line.decode().strip())
    process.wait()
    return process.returncode

def main():
    print("="*50)
    print("STARTING MODULE 6 VALIDATION PROTOCOL")
    print("="*50)

    # 1. Unit Tests
    print("\n[1/3] Running Unit Tests...")
    test_files = [
        "tests/test_intermarket/test_universe_mapper.py",
        "tests/test_intermarket/test_index_alignment.py",
        "tests/test_intermarket/test_sector_strength.py",
        "tests/test_intermarket/test_rs_breadth.py",
        "tests/test_intermarket/test_cross_global.py",
        "tests/test_intermarket/test_aggregator.py"
    ]
    
    env_str = "$env:PYTHONPATH = \".\";"
    cmd = f"powershell.exe -Command \"$env:PYTHONPATH = '.'; pytest " + " ".join(test_files) + "\""
    exit_code = run_command(cmd)
    
    if exit_code != 0:
        print("\n❌ Unit Tests Failed. Module not ready.")
        sys.exit(1)
        
    # 2. Beta Matrix Refresh Test
    print("\n[2/3] Testing Beta Matrix Refresh...")
    cmd_refresh = f"powershell.exe -Command \"$env:PYTHONPATH = '.'; python scripts/refresh_beta_matrix.py\""
    exit_code = run_command(cmd_refresh)
    if exit_code != 0:
        print("\n❌ Beta Refresh Failed.")
        sys.exit(1)

    # 3. Final Check
    print("\n" + "="*50)
    print("DONE: MODULE 6 READY FOR INTEGRATION")
    print("="*50)
    print("Summary of sub-components active:")
    print(" - SymbolUniverseMapper: Sector/Industry/Beta mappings loaded.")
    print(" - IndexAlignmentChecker: Nifty/BankNifty trend & IB alignment.")
    print(" - SectorStrengthAnalyzer: Relative sector ranking & breadth.")
    print(" - RelativeStrengthScorer: Beta-adjusted individual RS.")
    print(" - BreadthEngine: Market-wide ADR & Volume confirm.")
    print(" - CrossAssetContextEngine: USDINR/Crude/VIX sensitivity.")
    print(" - IntermarketAggregator: Weighted delta & Veto logic.")

if __name__ == "__main__":
    main()
