import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Directory containing validation files
base_dir = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\backtest_results\17_05_2026"

# Read all validation_metrics JSON files
metrics_list = []
json_files = sorted(Path(base_dir).glob("validation_metrics_20260517_*.json"))

print(f"📊 Found {len(json_files)} validation metric files")
print("=" * 120)
print()

# Parse all metrics
for json_file in json_files:
    with open(json_file, 'r') as f:
        data = json.load(f)
        summary = data.get('summary', {})
        timestamp = json_file.stem.replace("validation_metrics_", "")
        
        metrics_list.append({
            'timestamp': timestamp,
            'total_trades': summary.get('total_trades', 0),
            'win_rate_str': summary.get('win_rate', 'N/A'),
            'net_profit': summary.get('net_profit', 0),
            'profit_factor': summary.get('profit_factor', 0),
            'max_drawdown': summary.get('max_drawdown_pct', 'N/A'),
        })

# Create DataFrame
df = pd.DataFrame(metrics_list)

# Extract win rate as float for sorting
df['win_rate'] = df['win_rate_str'].str.rstrip('%').astype(float)

# Sort by net profit
df = df.sort_values('net_profit', ascending=False).reset_index(drop=True)

# Create master summary table
print("\n" + "=" * 120)
print("🏆 MASTER SUMMARY TABLE - ALL 69 STOCKS (SORTED BY NET PROFIT)")
print("=" * 120)
print()

summary_table = df[['timestamp', 'total_trades', 'win_rate_str', 'net_profit', 'profit_factor', 'max_drawdown']].copy()
summary_table.columns = ['Stock ID (Timestamp)', 'Total Trades', 'Win Rate', 'Net Profit (₹)', 'Profit Factor', 'Max Drawdown']
summary_table['Rank'] = range(1, len(summary_table) + 1)
summary_table = summary_table[['Rank', 'Stock ID (Timestamp)', 'Total Trades', 'Win Rate', 'Net Profit (₹)', 'Profit Factor', 'Max Drawdown']]

# Format currency
summary_table['Net Profit (₹)'] = summary_table['Net Profit (₹)'].apply(lambda x: f"₹{x:,.2f}")
summary_table['Profit Factor'] = summary_table['Profit Factor'].apply(lambda x: f"{x:.2f}")

print(summary_table.to_string(index=False))
print()

# Summary statistics
print("\n" + "=" * 120)
print("📈 AGGREGATE STATISTICS")
print("=" * 120)
total_profit = df['net_profit'].sum()
avg_profit = df['net_profit'].mean()
total_trades = df['total_trades'].sum()
avg_win_rate = df['win_rate'].mean()
best_profit = df['net_profit'].max()
worst_profit = df['net_profit'].min()

stats = {
    'Total P&L (All Stocks)': f'₹{total_profit:,.2f}',
    'Average P&L per Stock': f'₹{avg_profit:,.2f}',
    'Total Trades (All Stocks)': f'{total_trades:.0f}',
    'Average Win Rate': f'{avg_win_rate:.2f}%',
    'Best Stock P&L': f'₹{best_profit:,.2f}',
    'Worst Stock P&L': f'₹{worst_profit:,.2f}',
    'Number of Profitable Stocks': f'{(df["net_profit"] > 0).sum()} / {len(df)}',
}

for key, value in stats.items():
    print(f"{key:.<50} {value}")

print()

# Create individual stock tables
print("\n" + "=" * 120)
print("📊 INDIVIDUAL STOCK PERFORMANCE TABLES (69 STOCKS)")
print("=" * 120)

output_lines = []
output_lines.append("\n" + "=" * 120)
output_lines.append("INDIVIDUAL STOCK PERFORMANCE METRICS")
output_lines.append("=" * 120 + "\n")

for idx, row in df.iterrows():
    rank = idx + 1
    stock_id = row['timestamp']
    
    # Console output
    print(f"\n{'='*100}")
    print(f"📌 TABLE {rank}/69: Stock ID: {stock_id}")
    print(f"{'='*100}")
    
    # Create individual table
    table_data = {
        'Metric': [
            'Rank',
            'Total Trades',
            'Win Rate',
            'Net Profit',
            'Profit Factor',
            'Max Drawdown',
        ],
        'Value': [
            f"{rank} of {len(df)}",
            f"{row['total_trades']} trades",
            row['win_rate_str'],
            f"₹{row['net_profit']:,.2f}",
            f"{row['profit_factor']:.2f}",
            row['max_drawdown'],
        ]
    }
    
    table_df = pd.DataFrame(table_data)
    print(table_df.to_string(index=False))
    print()
    
    # File output
    output_lines.append(f"\n{'='*100}")
    output_lines.append(f"TABLE {rank}/69: Stock ID: {stock_id}")
    output_lines.append('='*100)
    output_lines.append("")
    output_lines.append(table_df.to_string(index=False))
    output_lines.append("")

print("\n✅ Analysis complete!")

# Export to files
print("\n" + "=" * 120)
print("💾 EXPORTING RESULTS")
print("=" * 120)

# Save summary CSV
summary_csv = os.path.join(base_dir, "SUMMARY_ALL_STOCKS_PERFORMANCE.csv")
summary_export = df[['timestamp', 'total_trades', 'win_rate_str', 'net_profit', 'profit_factor', 'max_drawdown']].copy()
summary_export.columns = ['Stock_ID', 'Total_Trades', 'Win_Rate', 'Net_Profit', 'Profit_Factor', 'Max_Drawdown_Pct']
summary_export.to_csv(summary_csv, index=False)
print(f"✓ Summary exported to: {summary_csv}")

# Save detailed report
report_txt = os.path.join(base_dir, "DETAILED_STOCK_PERFORMANCE_REPORT_69_STOCKS.txt")
with open(report_txt, 'w') as f:
    f.write("=" * 120 + "\n")
    f.write("STOCK-WISE PERFORMANCE ANALYSIS - MAY 17, 2026\n")
    f.write("OPTION TRADING BACKTEST RESULTS - 69 STOCKS\n")
    f.write("=" * 120 + "\n\n")
    
    f.write("MASTER SUMMARY TABLE\n")
    f.write("=" * 120 + "\n")
    f.write(summary_table.to_string(index=False))
    f.write("\n\n")
    
    f.write("=" * 120 + "\n")
    f.write("AGGREGATE STATISTICS\n")
    f.write("=" * 120 + "\n")
    for key, value in stats.items():
        f.write(f"{key:.<50} {value}\n")
    f.write("\n")
    
    f.write("\n".join(output_lines))

print(f"✓ Detailed report exported to: {report_txt}")

print(f"\n✅ All analysis complete! Check the exported files.")
