import os
import pandas as pd

CACHE_DIR = "data/cache"

class CachedDataLoader:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        self._mem = {}
    
    def load(self, symbol, interval="5m"):
        key = f"{symbol}_{interval}"
        if key in self._mem:
            return self._mem[key]
        
        # Try multiple naming conventions
        for fname in [f"{symbol}_{interval}.csv", f"{symbol}_{interval.replace('m','min')}.csv"]:
            path = os.path.join(self.cache_dir, fname)
            if os.path.exists(path):
                df = pd.read_csv(path)
                # Normalize timestamp column
                for col in ['Timestamp', 'timestamp', 'Date', 'date', 'datetime']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                        df.set_index(col, inplace=True)
                        break
                # Normalize OHLCV column names
                col_map = {}
                for c in df.columns:
                    cl = c.lower()
                    if 'open' in cl: col_map[c] = 'Open'
                    elif 'high' in cl: col_map[c] = 'High'
                    elif 'low' in cl: col_map[c] = 'Low'
                    elif 'close' in cl: col_map[c] = 'Close'
                    elif 'vol' in cl: col_map[c] = 'Volume'
                if col_map:
                    df.rename(columns=col_map, inplace=True)
                
                self._mem[key] = df
                return df
        return None
    
    def get_available_symbols(self, interval="5m"):
        symbols = set()
        if not os.path.exists(self.cache_dir):
            return []
        for f in os.listdir(self.cache_dir):
            if f.endswith('.csv') and interval in f:
                # Basic extraction of symbol from filename
                # Assumes format SYMBOL_interval.csv
                parts = f.split(f"_{interval}")
                if len(parts) > 1:
                    sym = parts[0]
                    if sym and sym != 'inventory':
                        symbols.add(sym)
        return sorted(symbols)
