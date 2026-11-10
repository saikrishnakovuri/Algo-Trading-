import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from modules.price_action_engine import PriceActionEngine

def draw_chart(symbol="RELIANCE", start_date="2026-03-24", end_date="2026-03-27"):
    file_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return

    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    df = df.loc[start_date:end_date]
    
    if df.empty:
        print("No data for selected range")
        return

    # Resample to 5m for cleaner visualization
    df_5m = PriceActionEngine.resample_data(df, "5min")
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Plot Candlesticks (Simplified)
    for idx, row in df_5m.iterrows():
        color = 'green' if row['Close'] >= row['Open'] else 'red'
        # Wick
        ax.plot([idx, idx], [row['Low'], row['High']], color='black', linewidth=1)
        # Body
        ax.add_patch(patches.Rectangle((idx - pd.Timedelta(minutes=2), min(row['Open'], row['Close'])), 
                                        pd.Timedelta(minutes=4), abs(row['Open'] - row['Close']),
                                        color=color, alpha=0.8))

    # Calculate and Draw Zones
    supports, resistances = PriceActionEngine.find_support_resistance(df_5m)
    
    for s in supports:
        low, high = s['zone']
        rect = patches.Rectangle((df_5m.index[0], low), df_5m.index[-1] - df_5m.index[0], high - low,
                                 color='blue', alpha=0.1, label='Support')
        ax.add_patch(rect)
        ax.text(df_5m.index[0], high, f" {s.get('label', 'S')}", color='blue', fontsize=10)

    for r in resistances:
        low, high = r['zone']
        rect = patches.Rectangle((df_5m.index[0], low), df_5m.index[-1] - df_5m.index[0], high - low,
                                 color='orange', alpha=0.1, label='Resistance')
        ax.add_patch(rect)
        ax.text(df_5m.index[0], low, f" {r.get('label', 'R')}", color='orange', fontsize=10)

    # Plot Trades from Journal
    journal_path = "trade_journal_ANGEL_HIST_30D.csv"
    if os.path.exists(journal_path):
        trades = pd.read_csv(journal_path)
        trades['date'] = pd.to_datetime(trades['date'], utc=True)
        symbol_trades = trades[trades['symbol'] == symbol]
        
        for _, t in symbol_trades.iterrows():
            if t['date'] in df_5m.index or (t['date'] >= df_5m.index[0] and t['date'] <= df_5m.index[-1]):
                color = 'cyan' if t['type'] == 'CE' else 'magenta'
                marker = '^' if t['type'] == 'CE' else 'v'
                ax.scatter(t['date'], t['entry'], color=color, s=200, marker=marker, edgecolors='black', label=f"Trade {t['type']}", zorder=5)
                ax.text(t['date'], t['entry'], f" {t['outcome']}\n ₹{t['pnl']}", fontsize=9, fontweight='bold')

    ax.set_title(f"Trading Pattern Analysis: {symbol} (5m Candles + Zones)")
    ax.set_ylabel("Price")
    ax.set_xlabel("Time")
    plt.grid(True, alpha=0.3)
    
    output_file = f"pattern_analysis_{symbol}.png"
    plt.savefig(output_file)
    print(f"✅ Pattern chart saved to {output_file}")

if __name__ == "__main__":
    draw_chart()
