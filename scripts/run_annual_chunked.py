import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from scripts.run_annual_compounded import AnnualCompoundedBacktester

# Override months for chunked execution
H1_MONTHS = [("2025-01-01", "2025-06-30")]
H2_MONTHS = [("2025-07-01", "2025-12-31")]

def run_chunk(months, initial_capital):
    tester = AnnualCompoundedBacktester()
    tester.pm.total_equity = initial_capital
    tester.run_custom(months)
    return tester.pm.total_equity

# Add run_custom to AnnualCompoundedBacktester class for H1/H2 support
# (Modifying the script to be dynamic)
if __name__ == "__main__":
    # Run H1
    print("🚀 Running H1 (Jan-Jun) 2025...")
    equity_h1 = run_chunk(H1_MONTHS, 500000.0)
    print(f"✅ H1 Complete. Ending Equity: {equity_h1:.2f}")
    
    # Run H2
    print(f"\n🚀 Running H2 (Jul-Dec) 2025 with compounded equity: {equity_h1:.2f}")
    equity_h2 = run_chunk(H2_MONTHS, equity_h1)
    print(f"✅ H2 Complete. Final Equity: {equity_h2:.2f}")
