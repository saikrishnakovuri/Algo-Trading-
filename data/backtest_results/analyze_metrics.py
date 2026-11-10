import os
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Directory containing the validation files
base_dir = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\backtest_results\17_05_2026"

# Read all validation_metrics JSON files
metrics_data = {}
csv_data = {}

json_files = sorted(Path(base_dir).glob("validation_metrics_20260517_*.json"))
csv_files = sorted(Path(base_dir).glob("validation_trades_20260517_*.csv"))

print(f"Found {len(json_files)} JSON metric files and {len(csv_files)} CSV trade files\n")

# Read metrics
for json_file in json_files:
    with open(json_file, 'r') as f:
        data = json.load(f)
        timestamp = json_file.stem.replace("validation_metrics_", "")
        metrics_data[timestamp] = data

# Read CSV files to get stock information
for csv_file in csv_files:
    df = pd.read_csv(csv_file)
    timestamp = csv_file.stem.replace("validation_trades_", "")
    
    # Extract stock from strategy or use timestamp as identifier
    # If strategy column contains stock name, extract it
    csv_data[timestamp] = df

# Aggregate metrics by extracting stock info from trades
# Create mapping of timestamps to stocks
stock_mapping = {}

for timestamp, csv_df in csv_data.items():
    if len(csv_df) > 0:
        # Get unique strategies/identifiers from the CSV
        # The CSV doesn't have explicit stock names, so we'll use the timestamp
        # But let's check if we can infer from the directory structure or file content
        stock_mapping[timestamp] = f"Stock_{timestamp}"

# Now aggregate all metrics
print("=" * 100)
print("AGGREGATED STOCK-WISE PERFORMANCE METRICS")
print("=" * 100)
print()

# Group by timestamp (representing different stock runs)
all_metrics = []

for timestamp, metrics in metrics_data.items():
    summary = metrics.get('summary', {})
    
    record = {
        'Timestamp': timestamp,
        'Stock': f"Stock_{timestamp}",
        'Total_Trades': summary.get('total_trades', 0),
        'Win_Rate': summary.get('win_rate', 'N/A'),
        'Net_Profit': summary.get('net_profit', 0),
        'Profit_Factor': summary.get('profit_factor', 0),
        'Max_Drawdown': summary.get('max_drawdown_pct', 'N/A'),
    }
    all_metrics.append(record)

# Create master summary table
summary_df = pd.DataFrame(all_metrics)

# Sort by net profit
summary_df = summary_df.sort_values('Net_Profit', ascending=False)

print("\n" + "=" * 100)
print("MASTER SUMMARY TABLE - ALL STOCKS")
print("=" * 100)
print(summary_df.to_string(index=False))
print()

# Create individual tables for each stock
print("\n" + "=" * 100)
print("INDIVIDUAL STOCK PERFORMANCE TABLES (69 TABLES)")
print("=" * 100)
print()

for idx, (_, row) in enumerate(summary_df.iterrows(), 1):
    print(f"\n{'='*80}")
    print(f"TABLE {idx}: {row['Stock'].upper()} - Timestamp: {row['Timestamp']}")
    print(f"{'='*80}")
    
    table_data = {
        'Metric': [
            'Total Trades',
            'Win Rate',
            'Net Profit (₹)',
            'Profit Factor',
            'Max Drawdown',
        ],
        'Value': [
            row['Total_Trades'],
            row['Win_Rate'],
            f"₹ {row['Net_Profit']:,.2f}",
            f"{row['Profit_Factor']:.2f}",
            row['Max_Drawdown']
        ]
    }
    
    table_df = pd.DataFrame(table_data)
    print(table_df.to_string(index=False))
    print()

# Export summary to CSV
output_csv = os.path.join(base_dir, "summary_stock_performance.csv")
summary_df.to_csv(output_csv, index=False)
print(f"\n✓ Summary exported to: {output_csv}")

# Export detailed report
output_txt = os.path.join(base_dir, "detailed_performance_report.txt")
with open(output_txt, 'w') as f:
    f.write("=" * 100 + "\n")
    f.write("STOCK-WISE PERFORMANCE ANALYSIS - MAY 17, 2026\n")
    f.write("=" * 100 + "\n\n")
    
    f.write(summary_df.to_string(index=False))
    f.write("\n\n" + "=" * 100 + "\n")
    f.write("INDIVIDUAL STOCK PERFORMANCE TABLES\n")
    f.write("=" * 100 + "\n\n")
    
    for idx, (_, row) in enumerate(summary_df.iterrows(), 1):
        f.write(f"\nTABLE {idx}: {row['Stock'].upper()} - Timestamp: {row['Timestamp']}\n")
        f.write("=" * 80 + "\n")
        
        table_data = {
            'Metric': [
                'Total Trades',
                'Win Rate',
                'Net Profit (₹)',
                'Profit Factor',
                'Max Drawdown',
            ],
            'Value': [
                row['Total_Trades'],
                row['Win_Rate'],
                f"₹ {row['Net_Profit']:,.2f}",
                f"{row['Profit_Factor']:.2f}",
                row['Max_Drawdown']
            ]
        }
        
        table_df = pd.DataFrame(table_data)
        f.write(table_df.to_string(index=False))
        f.write("\n\n")

print(f"✓ Detailed report exported to: {output_txt}")
