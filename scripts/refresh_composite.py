import os
import yaml
import pandas as pd
from pathlib import Path
from modules.vp_avwap.composite_profile import CompositeVolumeProfile

def main():
    # Load universe
    with open("config/universe.yaml", "r") as f:
        universe = yaml.safe_load(f)['universe']['symbols']
        
    # Load config
    with open("config/vp_avwap.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    cache_dir = config['composite'].get('cache_dir', 'data/composites/')
    windows = config['composite'].get('windows_days', [5, 20])
    
    composite_engine = CompositeVolumeProfile(config, cache_dir=cache_dir)
    
    data_dir = "data/nifty200"
    
    print(f"🚀 Refreshing Composite Volume Profiles for {len(universe)} symbols...")
    
    for symbol in universe[:10]: # Limit for speed in this demo
        file_path = os.path.join(data_dir, f"{symbol}_1m.csv")
        if not os.path.exists(file_path):
            print(f"⚠️ Data missing for {symbol}")
            continue
            
        print(f"📈 Processing {symbol}...")
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Calculate a reasonable ATR (e.g., from last day)
        atr_5m = 5.0 # Placeholder
        
        for w in windows:
            levels = composite_engine.compute_composite(df, atr_5m, w, symbol)
            if levels:
                composite_engine.save_to_cache(symbol, levels, w)
                print(f"   ✅ Saved {w}d composite POC: {levels['POC']}")

if __name__ == "__main__":
    main()
