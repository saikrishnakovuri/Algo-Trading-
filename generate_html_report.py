import os
import json
import pandas as pd
from pathlib import Path

# Directory containing validation files
base_dir = r"c:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\backtest_results\17_05_2026"

# Read CSV summary
csv_file = os.path.join(base_dir, "SUMMARY_ALL_STOCKS_PERFORMANCE.csv")
df = pd.read_csv(csv_file)

# Create HTML report
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Stock Performance Analysis - May 17, 2026</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .rank {
            font-weight: bold;
            color: #667eea;
            width: 50px;
            text-align: center;
        }
        .positive { color: #28a745; font-weight: bold; }
        .negative { color: #dc3545; font-weight: bold; }
        .neutral { color: #999; }
        .stock-table {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stock-card {
            background: white;
            border: 2px solid #eee;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .stock-card:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            border-color: #667eea;
        }
        .stock-card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .metric-label {
            font-weight: 600;
            color: #666;
        }
        .metric-value {
            font-weight: bold;
            color: #333;
        }
        .section-title {
            font-size: 1.8em;
            color: #333;
            margin: 40px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        .top-performers { background: linear-gradient(to right, #fff5f5, #fff0f0); }
        .poor-performers { background: linear-gradient(to right, #f5f5ff, #f0f0ff); }
    </style>
</head>
<body>
    <div class="container">
        <h1>Stock-Wise Performance Analysis</h1>
        <div class="subtitle">Option Trading Backtest Results - May 17, 2026</div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total P&L (All Stocks)</div>
                <div class="stat-value">Rs 6,928,185</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average P&L per Stock</div>
                <div class="stat-value">Rs 100,408</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value">7,524</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Profitable Stocks</div>
                <div class="stat-value">64 / 69</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average Win Rate</div>
                <div class="stat-value">39.12%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Best P&L</div>
                <div class="stat-value">Rs 1,404,728</div>
            </div>
        </div>

        <h2 class="section-title">Top 15 Performing Stocks</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">Rank</th>
                    <th>Stock ID</th>
                    <th style="width: 100px;">Trades</th>
                    <th style="width: 100px;">Win Rate</th>
                    <th>Net Profit (Rs)</th>
                    <th>Profit Factor</th>
                    <th>Max Drawdown</th>
                </tr>
            </thead>
            <tbody>
"""

# Add top 15 stocks
for idx, row in df.head(15).iterrows():
    html_content += f"""
                <tr class="top-performers">
                    <td class="rank">{idx + 1}</td>
                    <td>{row['Stock_ID']}</td>
                    <td style="text-align: center;">{row['Total_Trades']}</td>
                    <td style="text-align: center;">{row['Win_Rate']}</td>
                    <td class="positive">{row['Net_Profit']:,.2f}</td>
                    <td style="text-align: center;">{row['Profit_Factor']:.2f}</td>
                    <td>{row['Max_Drawdown_Pct']}</td>
                </tr>
"""

html_content += """
            </tbody>
        </table>

        <h2 class="section-title">Bottom 10 Performing Stocks</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">Rank</th>
                    <th>Stock ID</th>
                    <th style="width: 100px;">Trades</th>
                    <th style="width: 100px;">Win Rate</th>
                    <th>Net Profit (Rs)</th>
                    <th>Profit Factor</th>
                    <th>Max Drawdown</th>
                </tr>
            </thead>
            <tbody>
"""

# Add bottom 10 stocks
for idx, row in df.tail(10).iterrows():
    html_content += f"""
                <tr class="poor-performers">
                    <td class="rank">{idx + 1}</td>
                    <td>{row['Stock_ID']}</td>
                    <td style="text-align: center;">{row['Total_Trades']}</td>
                    <td style="text-align: center;">{row['Win_Rate']}</td>
                    <td class="negative">{row['Net_Profit']:,.2f}</td>
                    <td style="text-align: center;">{row['Profit_Factor']:.2f}</td>
                    <td>{row['Max_Drawdown_Pct']}</td>
                </tr>
"""

html_content += """
            </tbody>
        </table>

        <h2 class="section-title">All 69 Stocks Individual Performance Cards</h2>
        <div class="stock-table">
"""

# Add all 69 stocks as cards
for idx, row in df.iterrows():
    color = "#28a745" if row['Net_Profit'] > 0 else "#dc3545"
    html_content += f"""
            <div class="stock-card">
                <h3>#{idx + 1} - {row['Stock_ID']}</h3>
                <div class="metric-row">
                    <span class="metric-label">Total Trades:</span>
                    <span class="metric-value">{row['Total_Trades']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Win Rate:</span>
                    <span class="metric-value">{row['Win_Rate']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Net Profit:</span>
                    <span class="metric-value" style="color: {color};">Rs {row['Net_Profit']:,.2f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Profit Factor:</span>
                    <span class="metric-value">{row['Profit_Factor']:.2f}</span>
                </div>
                <div class="metric-row" style="border: none;">
                    <span class="metric-label">Max Drawdown:</span>
                    <span class="metric-value">{row['Max_Drawdown_Pct']}</span>
                </div>
            </div>
"""

html_content += """
        </div>
    </div>
</body>
</html>
"""

# Save HTML
output_html = os.path.join(base_dir, "STOCK_PERFORMANCE_ANALYSIS.html")
with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML report generated: {output_html}")
