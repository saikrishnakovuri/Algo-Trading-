import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import logging
from scripts.validation_backtest import ValidationBacktester

# Silence debug spam for the annual run
logging.getLogger("SMC_Engine").setLevel(logging.WARNING)
logging.getLogger("SMC_Structure").setLevel(logging.WARNING)
logging.getLogger("modules.strategy_selector").setLevel(logging.WARNING)
logging.getLogger("modules.mean_reversion_engine").setLevel(logging.WARNING)

MONTHS = [
    ("2025-01-01", "2025-01-31"),
    ("2025-02-01", "2025-02-28"),
    ("2025-03-01", "2025-03-31"),
    ("2025-04-01", "2025-04-30"),
    ("2025-05-01", "2025-05-31"),
    ("2025-06-01", "2025-06-30"),
    ("2025-07-01", "2025-07-31"),
    ("2025-08-01", "2025-08-31"),
    ("2025-09-01", "2025-09-30"),
    ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30"),
    ("2025-12-01", "2025-12-31")
]

symbol = "RELIANCE"
print(f"--- Running 2025 Annual Backtest for {symbol} ---")

tester = ValidationBacktester(initial_capital=500000.0)
tester.master.mode = "BALANCED"

annual_results = []
for start, end in MONTHS:
    print(f"Processing {start} to {end}...")
    tester.run_for_symbol(symbol, start, end)
    
    # Isolate trades for this month
    df = pd.DataFrame(tester.trade_log)
    if not df.empty:
        # Filter trades that occurred in this month
        df['date'] = pd.to_datetime(df['timestamp'])
        month_df = df[(df['date'] >= start) & (df['date'] <= end)]
        
        if not month_df.empty:
            wins = len(month_df[month_df['net_pnl'] > 0])
            total = len(month_df)
            annual_results.append({
                "Month": start[:7],
                "Trades": total,
                "Win Rate": f"{(wins/total)*100:.1f}%",
                "Net PnL": round(month_df['net_pnl'].sum(), 2)
            })

print("\n--- MONTHLY BREAKDOWN ---")
if annual_results:
    print(pd.DataFrame(annual_results).to_markdown(index=False))
else:
    print("No trades found.")

# Overall metrics
df_all = pd.DataFrame(tester.trade_log)
if not df_all.empty:
    wins = len(df_all[df_all['net_pnl'] > 0])
    total = len(df_all)
    pf = abs(df_all[df_all['net_pnl'] > 0]['net_pnl'].sum() / df_all[df_all['net_pnl'] < 0]['net_pnl'].sum()) if not df_all[df_all['net_pnl'] < 0].empty else 99.0
    print(f"\n--- ANNUAL TOTALS ---")
    print(f"Total Trades: {total}")
    print(f"Win Rate: {(wins/total)*100:.1f}%")
    print(f"Net PnL: ₹{df_all['net_pnl'].sum():.2f}")
    print(f"Profit Factor: {pf:.2f}")
    print(f"Max Drawdown: {tester._calculate_drawdown(df_all['net_pnl'])}")
