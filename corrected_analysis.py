import pandas as pd
import os

# Read the CSV
base_dir = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\backtest_results\17_05_2026"
csv_file = os.path.join(base_dir, "SUMMARY_ALL_STOCKS_PERFORMANCE.csv")
df = pd.read_csv(csv_file)

# Identify corrupted stocks (0% win rate)
corrupted = df[df['Win_Rate'] == '0.00%']
valid_df = df[df['Win_Rate'] != '0.00%']

print("=" * 100)
print("CORRECTED ANALYSIS - EXCLUDING CORRUPTED DATA")
print("=" * 100)
print()

print(f"Total Stocks Analyzed: {len(df)}")
print(f"Corrupted Stocks (0% Win Rate): {len(corrupted)}")
print(f"Valid Stocks: {len(valid_df)}")
print()

print("CORRUPTED STOCKS IDENTIFIED:")
print("-" * 100)
for idx, row in corrupted.iterrows():
    print(f"  #{idx+1}: {row['Stock_ID']} - {row['Total_Trades']} trades, all -70.0 = {row['Net_Profit']} P&L")
print()

print("=" * 100)
print("CORRECTED STATISTICS (EXCLUDING 3 CORRUPTED STOCKS)")
print("=" * 100)
print()

total_profit = valid_df['Net_Profit'].sum()
avg_profit = valid_df['Net_Profit'].mean()
total_trades = valid_df['Total_Trades'].sum()
profitable_count = (valid_df['Net_Profit'] > 0).sum()

# Extract win rate as float
valid_df_temp = valid_df.copy()
valid_df_temp['Win_Rate_Float'] = valid_df_temp['Win_Rate'].str.rstrip('%').astype(float)
avg_win_rate = valid_df_temp['Win_Rate_Float'].mean()

stats = {
    'Total Stocks (Valid)': len(valid_df),
    'Total P&L': f'Rs {total_profit:,.2f}',
    'Average P&L per Stock': f'Rs {avg_profit:,.2f}',
    'Total Trades': f'{total_trades:.0f}',
    'Average Win Rate': f'{avg_win_rate:.2f}%',
    'Profitable Stocks': f'{profitable_count} / {len(valid_df)}',
    'Profitability Rate': f'{(profitable_count/len(valid_df)*100):.2f}%',
    'Best P&L': f'Rs {valid_df["Net_Profit"].max():,.2f}',
    'Worst P&L (Loss)': f'Rs {valid_df[valid_df["Net_Profit"]<0]["Net_Profit"].min():,.2f}',
}

for key, value in stats.items():
    print(f"{key:.<40} {value}")

print()
print("=" * 100)
print("TOP 10 STOCKS (VALID DATA)")
print("=" * 100)
print()

top_10 = valid_df.nlargest(10, 'Net_Profit')
for idx, (_, row) in enumerate(top_10.iterrows(), 1):
    print(f"{idx:2}. {row['Stock_ID']} | Trades: {row['Total_Trades']:3} | WR: {row['Win_Rate']:>6} | "
          f"P&L: Rs {row['Net_Profit']:>12,.2f} | PF: {row['Profit_Factor']:>6.2f}")

print()
print("=" * 100)
print("BOTTOM 5 VALID STOCKS (LOWEST PROFITS)")
print("=" * 100)
print()

bottom_5 = valid_df.nsmallest(5, 'Net_Profit')
for idx, (_, row) in enumerate(bottom_5.iterrows(), 1):
    print(f"{idx}. {row['Stock_ID']} | Trades: {row['Total_Trades']:3} | WR: {row['Win_Rate']:>6} | "
          f"P&L: Rs {row['Net_Profit']:>12,.2f} | PF: {row['Profit_Factor']:>6.2f}")

print()
print("=" * 100)
print("KEY INSIGHT")
print("=" * 100)
print()
print(f"✓ Excluding 3 corrupted stocks with uniform -70.0 P&L per trade")
print(f"✓ Revised analysis based on {len(valid_df)} valid, realistic stocks")
print(f"✓ Overall performance: {profitable_count}/{len(valid_df)} profitable = {(profitable_count/len(valid_df)*100):.2f}%")
print(f"✓ Total valid P&L: Rs {total_profit:,.2f}")
print()
