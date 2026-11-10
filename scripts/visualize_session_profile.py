import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yaml
import os
from modules.vp_avwap.session_profile import SessionVolumeProfile

def main():
    # Load sample data
    file_path = "data/nifty200/RELIANCE_1m.csv"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    # Filter for one day
    target_date = "2026-04-16"
    day_df = df[df.index.strftime('%Y-%m-%d') == target_date].copy()
    
    if day_df.empty:
        print(f"No data for {target_date}")
        return

    # Load config
    with open("config/vp_avwap.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    vp_engine = SessionVolumeProfile(config)
    
    # Calculate ATR for bin size
    atr_5m = 5.0 # Approximate for RELIANCE
    profile = vp_engine.compute(day_df, atr_5m=atr_5m, tick_size=0.05)
    
    print("📊 Volume Profile computed for RELIANCE on", target_date)
    print(f"POC: {profile['POC']}")
    print(f"VAH: {profile['VAH']}")
    print(f"VAL: {profile['VAL']}")
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={'width_ratios': [3, 1]})
    
    from modules.vp_avwap.anchored_vwap import AnchoredVWAPEngine
    avwap_engine = AnchoredVWAPEngine(config)
    
    # Resample for 5m swings
    day_df_5m = day_df.resample('5min').apply({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    prior_ohlc = {'close': day_df['Close'].iloc[0]} # Simplified
    
    avwaps = avwap_engine.compute_all(day_df, prior_ohlc, day_df_5m, atr_5m)
    
    # Plot Candles on ax1
    ax1.plot(day_df.index, day_df['Close'], color='black', alpha=0.5)
    ax1.fill_between(day_df.index, day_df['Low'], day_df['High'], color='gray', alpha=0.2)
    
    # Plot POC, VAH, VAL
    ax1.axhline(profile['POC'], color='red', linestyle='--', label='POC')
    ax1.axhline(profile['VAH'], color='blue', linestyle=':', label='VAH')
    ax1.axhline(profile['VAL'], color='blue', linestyle=':', label='VAL')
    
    # Plot AVWAPs
    colors = ['green', 'purple', 'orange', 'cyan']
    for i, (name, val) in enumerate(avwaps.items()):
        color = colors[i % len(colors)]
        ax1.axhline(val['value'], color=color, label=f"AVWAP: {name}")
        ax1.axhline(val['+1sd'], color=color, linestyle='--', alpha=0.3)
        ax1.axhline(val['-1sd'], color=color, linestyle='--', alpha=0.3)
    ax1.legend()
    ax1.set_title(f"RELIANCE 1m - {target_date}")
    
    # Plot Profile Histogram on ax2
    # We need the raw bin volumes which I should probably expose for visualization
    # Recomputing briefly for plot
    bin_size = profile['bin_size']
    min_p, max_p = day_df['Low'].min(), day_df['High'].max()
    bin_edges = np.arange(min_p - bin_size, max_p + 2*bin_size, bin_size)
    bin_volumes = np.zeros(len(bin_edges) - 1)
    
    from modules.vp_avwap.session_profile import distribute_volume_numba
    distribute_volume_numba(
        day_df['Low'].values, day_df['High'].values, day_df['Close'].values, 
        day_df['Volume'].values, bin_edges, bin_volumes
    )
    
    ax2.barh(bin_edges[:-1], bin_volumes, height=bin_size, color='gray', alpha=0.5)
    ax2.axhline(profile['POC'], color='red', linestyle='--')
    ax2.axhline(profile['VAH'], color='blue', linestyle=':')
    ax2.axhline(profile['VAL'], color='blue', linestyle=':')
    ax2.set_title("Volume Profile")
    
    output_img = "notebooks/session_profile_reliance.png"
    plt.savefig(output_img)
    print(f"✅ Plot saved to {output_img}")

if __name__ == "__main__":
    main()
