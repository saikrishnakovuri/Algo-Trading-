"""Pre-computed indicator cache. Single-pass O(N) calculation, then per-bar O(1) lookup."""
import pandas as pd
import numpy as np

def precompute_indicators(df_5m: pd.DataFrame) -> pd.DataFrame:
    """
    Add indicator columns to df_5m.
    Computes: ema9, ema20, ema50, rsi, atr, vwap, vwap_dist_pct, bb_*, etc.
    """
    df = df_5m
    df.columns = [c.lower() for c in df.columns]
    
    # --- 1. BASIC EMAs ---
    if 'ema9' not in df.columns:
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    if 'ema20' not in df.columns:
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    if 'ema50' not in df.columns:
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
    # --- 2. RSI (Wilder's) ---
    if 'rsi' not in df.columns:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
        
    if 'rsi_slope' not in df.columns:
        df['rsi_slope'] = df['rsi'] - df['rsi'].shift(3)
        
    # --- 3. ATR ---
    if 'tr_atr' not in df.columns:
        h, l, c = df['high'], df['low'], df['close'].shift(1)
        tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
        df['tr_atr'] = tr.rolling(14, min_periods=1).mean()
    
    if 'atr' not in df.columns:
        # Simple ATR for backward compatibility
        df['atr'] = (df['high'] - df['low']).rolling(14, min_periods=1).mean()
        
    if 'atr_avg' not in df.columns:
        df['atr_avg'] = df['tr_atr'].rolling(20, min_periods=1).mean()
        
    if 'atr_expansion' not in df.columns:
        atr_avg50 = df['tr_atr'].rolling(window=50, min_periods=10).mean()
        df['atr_expansion'] = df['tr_atr'] / atr_avg50.replace(0, np.nan)

    # --- 4. VWAP ---
    if 'vwap' not in df.columns:
        if 'volume' in df.columns and df['volume'].sum() > 0:
            typical_price = (df['high'] + df['low'] + df['close']) / 3.0
            vol = df['volume'].replace(0, 1)
            # Session VWAP
            df['vwap'] = (typical_price * vol).groupby(df.index.date).cumsum() / vol.groupby(df.index.date).cumsum()
            # Close-based VWAP (used by signal_adapter)
            df['vwap_close'] = (df['close'] * vol).groupby(df.index.date).cumsum() / vol.groupby(df.index.date).cumsum()
        else:
            df['vwap'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['vwap_close'] = df['vwap']
            
    if 'vwap_dist_pct' not in df.columns:
        df['vwap_dist_pct'] = ((df['close'] - df['vwap']) / df['vwap']) * 100.0

    # --- 5. BOLLINGER BANDS ---
    if 'bb_mid' not in df.columns:
        df['bb_mid'] = df['close'].rolling(window=20, min_periods=1).mean()
        bb_std = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_std'] = bb_std
        df['bb_upper_2'] = df['bb_mid'] + (2.0 * bb_std)
        df['bb_lower_2'] = df['bb_mid'] - (2.0 * bb_std)
        df['bb_upper_3'] = df['bb_mid'] + (3.0 * bb_std)
        df['bb_lower_3'] = df['bb_mid'] - (3.0 * bb_std)
        bb_range = df['bb_upper_2'] - df['bb_lower_2']
        df['bb_pct_b'] = (df['close'] - df['bb_lower_2']) / bb_range.replace(0, np.nan)

    if 'vwap_std' not in df.columns:
        if 'volume' in df.columns and df['volume'].sum() > 0:
            typical_price = (df['high'] + df['low'] + df['close']) / 3.0
            vol = df['volume'].replace(0, 1)
            cum_vol = vol.groupby(df.index.date).cumsum()
            vwap_var = ((typical_price - df['vwap'])**2 * vol).groupby(df.index.date).cumsum() / cum_vol
            df['vwap_std'] = np.sqrt(vwap_var.clip(lower=0))
        else:
            df['vwap_std'] = df['close'].rolling(window=20, min_periods=1).std()
            
        df['vwap_upper_1_5'] = df['vwap'] + (1.5 * df['vwap_std'])
        df['vwap_lower_1_5'] = df['vwap'] - (1.5 * df['vwap_std'])
        df['vwap_upper_2_5'] = df['vwap'] + (2.5 * df['vwap_std'])
        df['vwap_lower_2_5'] = df['vwap'] - (2.5 * df['vwap_std'])

    # --- 6. MISC ---
    if 'ema_spread_pct' not in df.columns:
        df['ema_spread_pct'] = ((df['ema9'] - df['ema20']) / df['close']) * 100.0
        
    if 'vol_ratio' not in df.columns and 'volume' in df.columns:
        vol_avg = df['volume'].rolling(window=20, min_periods=1).mean()
        df['vol_ratio'] = df['volume'] / vol_avg.replace(0, np.nan)

    if 'body' not in df.columns:
        df['body'] = (df['close'] - df['open']).abs()
        df['range'] = df['high'] - df['low']
        df['body_ratio'] = df['body'] / df['range'].replace(0, np.nan)
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_bullish'] = df['close'] > df['open']

    # --- 7. ROLLING HIGHS/LOWS ---
    if 'highest20' not in df.columns:
        df['highest20'] = df['high'].rolling(20, min_periods=1).max().shift(1)
    if 'lowest20' not in df.columns:
        df['lowest20'] = df['low'].rolling(20, min_periods=1).min().shift(1)

    if 'rolling_high20' not in df.columns:
        df['rolling_high20'] = df['high'].rolling(20, min_periods=1).max()
    if 'rolling_low20' not in df.columns:
        df['rolling_low20'] = df['low'].rolling(20, min_periods=1).min()

    # ALIASES for per-engine expectations
    df['ema_fast'] = df['ema9']
    df['ema_slow'] = df['ema20']

    return df
