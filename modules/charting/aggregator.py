import os
import pandas as pd
import numpy as np
import yaml
from datetime import datetime, time
from typing import Dict, Any, List, Optional, Union

class ChartDataAggregator:
    def __init__(self, config_path: str = "config/charting.yaml"):
        with open(config_path, "r", encoding='utf-8') as f:
            self.config = yaml.safe_load(f)["charting"]
        
        self.market_open = datetime.strptime(self.config["session"]["market_open"], "%H:%M").time()
        self.market_close = datetime.strptime(self.config["session"]["market_close"], "%H:%M").time()

    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """Load raw 1m CSV data into standardized DataFrame."""
        try:
            df = pd.read_csv(filepath)
            
            # Combine Date and Time into a single index
            if 'date' in df.columns and 'time' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
            elif 'timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['timestamp'])
            else:
                # Attempt to find a timestamp-like column
                ts_cols = [c for f in ['time', 'date', 'Timestamp', 'datetime'] for c in df.columns if f.lower() in c.lower()]
                if ts_cols:
                    df['Timestamp'] = pd.to_datetime(df[ts_cols[0]])
            
            df.set_index('Timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Standardize column names
            col_map = {
                'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume',
                'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'
            }
            df.rename(columns={c: col_map[c.lower()] for c in df.columns if c.lower() in col_map}, inplace=True)
            
            # Keep only OHLCV
            required = ['open', 'high', 'low', 'close', 'volume']
            df = df[[c for c in required if c in df.columns]]
            
            df.dropna(inplace=True)
            df = df[~df.index.duplicated(keep='first')]
            
            return df
        except Exception as e:
            print(f"Error loading CSV {filepath}: {e}")
            return pd.DataFrame()

    def load_from_redis(self, token: str, timeframe: str = '1m', count: int = 500) -> pd.DataFrame:
        """Load candle data from Redis (mocking implementation for now)."""
        # In a real scenario, we would import redis_data_reader here.
        # This keeps the logic consistent with the planned structure.
        try:
            from modules.data.redis_data_reader import RedisDataReader
            reader = RedisDataReader()
            key = f"candles:{timeframe}:NSE:{token}"
            data = reader.get_latest_candles(key, count)
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['Timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('Timestamp', inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception:
            return pd.DataFrame()

    def resample(self, df_1m: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample 1m data to any higher timeframe with cross-session prevention."""
        if timeframe == '1m' or df_1m.empty:
            return df_1m
        
        # Map user timeframes to pandas frequency aliases
        tf_map = {
            '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', 
            '30m': '30min', '1h': '1H', '4h': '4H', '1D': '1D'
        }
        pd_tf = tf_map.get(timeframe, timeframe)

        # Aggregate by session (date) to prevent cross-day bars
        def resample_session(session_df):
            return session_df.resample(pd_tf).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()


        # Group by date and apply resampling
        resampled_df = df_1m.groupby(df_1m.index.date).apply(resample_session)
        
        # Drop the extra index level created by groupby(date)
        if not resampled_df.empty:
            resampled_df.index = resampled_df.index.get_level_values(1)
            
        return resampled_df

    def compute_volume_profile(self, df: pd.DataFrame, num_bins: int = None) -> dict:
        """Compute Volume Profile (volume at each price level)."""
        if df.empty: return {}
        
        num_bins = num_bins or self.config["volume_profile"]["num_bins"]
        va_pct = self.config["volume_profile"]["value_area_pct"] / 100.0
        
        price_min = df['low'].min()
        price_max = df['high'].max()
        
        if price_max == price_min:
            return {'poc': price_min, 'total_volume': df['volume'].sum()}

        bin_size = (price_max - price_min) / num_bins
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_volumes = np.zeros(num_bins)
        
        # Distribute volume across bins touched by each candle
        for _, row in df.iterrows():
            low, high, vol = row['low'], row['high'], row['volume']
            # Find indices of bins that intersect with [low, high]
            touched_indices = np.where((bins[:-1] < high) & (bins[1:] > low))[0]
            if len(touched_indices) > 0:
                vol_per_bin = vol / len(touched_indices)
                bin_volumes[touched_indices] += vol_per_bin

        # 1. Point of Control (POC)
        poc_idx = np.argmax(bin_volumes)
        poc_price = (bins[poc_idx] + bins[poc_idx+1]) / 2
        
        # 2. Value Area
        total_vol = bin_volumes.sum()
        target_va_vol = total_vol * va_pct
        
        va_vol = bin_volumes[poc_idx]
        low_idx = poc_idx
        high_idx = poc_idx
        
        # Expand from POC
        while va_vol < target_va_vol and (low_idx > 0 or high_idx < num_bins - 1):
            prev_low_vol = bin_volumes[low_idx - 1] if low_idx > 0 else 0
            next_high_vol = bin_volumes[high_idx + 1] if high_idx < num_bins - 1 else 0
            
            if prev_low_vol >= next_high_vol and low_idx > 0:
                va_vol += prev_low_vol
                low_idx -= 1
            elif high_idx < num_bins - 1:
                va_vol += next_high_vol
                high_idx += 1
            else:
                break
                
        va_low = bins[low_idx]
        va_high = bins[high_idx + 1]

        # 3. Nodes
        sorted_indices = np.argsort(bin_volumes)
        hvn = [((bins[i] + bins[i+1])/2, bin_volumes[i]) for i in sorted_indices[-5:][::-1]]
        lvn = [((bins[i] + bins[i+1])/2, bin_volumes[i]) for i in sorted_indices[:5]]

        return {
            'bins': list(zip(bins[:-1], bins[1:], bin_volumes)),
            'poc': float(poc_price),
            'va_high': float(va_high),
            'va_low': float(va_low),
            'total_volume': int(total_vol),
            'high_volume_nodes': hvn,
            'low_volume_nodes': lvn
        }

    def compute_session_stats(self, df_1m: pd.DataFrame) -> dict:
        """Compute per-session statistics including PDH/PDL and IB."""
        if df_1m.empty: return {}
        
        sessions = {}
        grouped = df_1m.groupby(df_1m.index.date)
        dates = sorted(grouped.groups.keys())
        
        prev_high = None
        prev_low = None
        
        for i, d in enumerate(dates):
            sdf = grouped.get_group(d)
            
            # Session Basics
            s_open = sdf.iloc[0]['open']
            s_close = sdf.iloc[-1]['close']
            s_high = sdf['high'].max()
            s_low = sdf['low'].min()
            s_vol = sdf['volume'].sum()
            
            # Initial Balance (09:15 - 09:45)
            ib_end_time = time(9, 45)
            ib_df = sdf[sdf.index.time <= ib_end_time]
            ib_high = ib_df['high'].max() if not ib_df.empty else None
            ib_low = ib_df['low'].min() if not ib_df.empty else None
            
            # IB Extension
            post_ib_df = sdf[sdf.index.time > ib_end_time]
            ib_ext_up = (post_ib_df['high'].max() > ib_high) if ib_high and not post_ib_df.empty else False
            ib_ext_down = (post_ib_df['low'].min() < ib_low) if ib_low and not post_ib_df.empty else False
            
            sessions[str(d)] = {
                'open': s_open, 'high': s_high, 'low': s_low, 'close': s_close, 'volume': s_vol,
                'pdh': prev_high,
                'pdl': prev_low,
                'ib_high': ib_high,
                'ib_low': ib_low,
                'ib_extended_up': ib_ext_up,
                'ib_extended_down': ib_ext_down
            }
            
            # Update for next day
            prev_high = s_high
            prev_low = s_low
            
        return sessions

    def build_chart_data(self, filepath_or_df: Union[str, pd.DataFrame], timeframes: List[str] = None) -> dict:
        """Load data -> resample -> compute VP for each timeframe."""
        if isinstance(filepath_or_df, str):
            df_1m = self.load_from_csv(filepath_or_df)
        else:
            df_1m = filepath_or_df
            
        if df_1m.empty: return {}
        
        timeframes = timeframes or self.config["default_timeframes"]
        result = {'session_stats': self.compute_session_stats(df_1m)}
        
        for tf in timeframes:
            res_df = self.resample(df_1m, tf)
            result[tf] = {
                'candles': res_df,
                'volume_profile': self.compute_volume_profile(res_df)
            }
            
        return result

if __name__ == "__main__":
    # This block is for documentation only and won't be run automatically.
    print("ChartDataAggregator module ready.")
