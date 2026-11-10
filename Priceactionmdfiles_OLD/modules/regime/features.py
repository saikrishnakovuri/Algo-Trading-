import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
import ta
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

class FeatureCalculator:
    """
    Computes all 10 features required for Market Regime Classification.
    """

    @staticmethod
    def _get_col(df: pd.DataFrame, names: list):
        for name in names:
            if name in df.columns:
                return df[name]
        # Fallback to searching case-insensitive
        cols_lower = {c.lower(): c for c in df.columns}
        for name in names:
            if name.lower() in cols_lower:
                return df[cols_lower[name.lower()]]
        raise KeyError(f"None of {names} found in columns {df.columns}")

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
        """Wilder's ADX, period 14."""
        if len(df) < period * 2:
            return 0.0
        h = FeatureCalculator._get_col(df, ['high', 'High'])
        l = FeatureCalculator._get_col(df, ['low', 'Low'])
        c = FeatureCalculator._get_col(df, ['close', 'Close'])
        adx_ind = ADXIndicator(high=h, low=l, close=c, window=period)
        val = adx_ind.adx().iloc[-1]
        return float(val) if not np.isnan(val) else 0.0

    @staticmethod
    def calculate_choppiness(df: pd.DataFrame, n: int = 14) -> float:
        """
        Choppiness Index, Bhargava formula:
        CI = 100 * log10(sum(TR, n) / (max(H,n) - min(L,n))) / log10(n)
        """
        if len(df) < n:
            return 50.0 # Default to random/neutral

        h = FeatureCalculator._get_col(df, ['high', 'High'])
        l = FeatureCalculator._get_col(df, ['low', 'Low'])
        c = FeatureCalculator._get_col(df, ['close', 'Close'])

        # True Range
        high_low = h - l
        high_prev_close = (h - c.shift(1)).abs()
        low_prev_close = (l - c.shift(1)).abs()
        tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)

        sum_tr = tr.rolling(n).sum().iloc[-1]
        max_h = h.rolling(n).max().iloc[-1]
        min_l = l.rolling(n).min().iloc[-1]

        range_hl = max_h - min_l
        if range_hl == 0:
            return 100.0

        ci = 100 * np.log10(sum_tr / range_hl) / np.log10(n)
        return float(ci) if not np.isnan(ci) else 50.0
    @staticmethod
    def calculate_hurst(series: pd.Series, window: int = 100) -> float:
        """
        Hurst Exponent using R/S analysis (Manual Implementation).
        >0.55 = trending, <0.45 = mean-reverting, ~0.50 = random.
        """
        if len(series) < window:
            return 0.5
            
        y = series.iloc[-window:].values
        n = len(y)
        
        def get_rs(data):
            # Calculate Rescaled Range for a single sequence
            m = np.mean(data)
            z = np.cumsum(data - m)
            r = np.max(z) - np.min(z)
            s = np.std(data)
            return r / s if s != 0 else 0
            
        # Simplified R/S: only use a few sub-window sizes
        lags = [10, 20, 40, 80] if n >= 100 else [5, 10, 20]
        rs_values = []
        for lag in lags:
            res = []
            for i in range(0, n - lag + 1, lag):
                rs = get_rs(y[i:i+lag])
                if rs > 0: res.append(rs)
            if res:
                rs_values.append((np.log(lag), np.log(np.mean(res))))
        
        if len(rs_values) < 2:
            return 0.5
            
        # Fit linear regression to log(lag) vs log(R/S)
        x_coords, y_coords = zip(*rs_values)
        slope, _ = np.polyfit(x_coords, y_coords, 1)
        return float(slope)

    @staticmethod
    def calculate_rv_ratio(df: pd.DataFrame, window_avg: int = 20) -> float:
        """
        Realised vol ratio:
        RV_5m_today (sum of squared log returns, annualised) 
        / RV_20day_avg (same metric, 20-session mean)
        """
        if len(df) < 50: # Need enough for returns and avg
            return 1.0
            
        log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
        if log_returns.empty:
            return 1.0
            
        # Realized Volatility (Annualized) - Approx 75 5m bars per day in NSE
        # We'll use a rolling sum of squared returns for "today" (last 75 bars)
        bars_per_day = 75 
        current_rv = np.sqrt(np.sum(log_returns.iloc[-bars_per_day:]**2) * 252)
        
        # 20-day average RV
        # For simplicity in 5m data, we look at the last 20 * 75 bars
        historical_rvs = []
        for i in range(window_avg):
            start = -(i+1)*bars_per_day
            end = -i*bars_per_day if i > 0 else None
            period_returns = log_returns.iloc[start:end]
            if not period_returns.empty:
                rv = np.sqrt(np.sum(period_returns**2) * 252)
                historical_rvs.append(rv)
        
        avg_rv = np.mean(historical_rvs) if historical_rvs else 1.0
        ratio = current_rv / avg_rv if avg_rv > 0 else 1.0
        return float(ratio)

    @staticmethod
    def calculate_vix_slope(vix_history: pd.Series) -> float:
        """5-day % change in India VIX. >15% = vol spike."""
        if len(vix_history) < 5:
            return 0.0
        v_start = vix_history.iloc[-5]
        v_end = vix_history.iloc[-1]
        if v_start == 0: return 0.0
        slope = (v_end - v_start) / v_start * 100
        return float(slope)

    @staticmethod
    def calculate_atr_percentile(df_nifty: pd.DataFrame, period: int = 14, lookback: int = 252) -> float:
        """Percentile rank (0–100) of today's Nifty ATR_14 vs last 252 sessions."""
        if len(df_nifty) < lookback:
            return 50.0
            
        atr_ind = AverageTrueRange(high=df_nifty['high'], low=df_nifty['low'], close=df_nifty['close'], window=period)
        atr_series = atr_ind.average_true_range()
        
        current_atr = atr_series.iloc[-1]
        hist_atrs = atr_series.iloc[-lookback:]
        
        if hist_atrs.empty: return 50.0
        rank = (hist_atrs < current_atr).mean() * 100
        return float(rank)

    @staticmethod
    def calculate_range_ratio(df: pd.DataFrame, window: int = 12, atr_period: int = 14) -> float:
        """(5m_high − 5m_low, last 12 bars) / ATR_14_5m"""
        if len(df) < max(window, atr_period):
            return 1.0
            
        recent_high = df['high'].iloc[-window:].max()
        recent_low = df['low'].iloc[-window:].min()
        recent_range = recent_high - recent_low
        
        atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=atr_period)
        current_atr = atr_ind.average_true_range().iloc[-1]
        
        if current_atr == 0: return 1.0
        return float(recent_range / current_atr)

    @staticmethod
    def calculate_volume_ratio(df: pd.DataFrame, rolling_avg_days: int = 20) -> float:
        """current cumulative volume / rolling 20-day avg at same time-of-day."""
        # Note: This requires time-of-day alignment which is complex without full history.
        # Simplified: Current volume / avg volume of last 20 bars
        if len(df) < rolling_avg_days:
            return 1.0
        current_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].iloc[-rolling_avg_days:].mean()
        if avg_vol == 0: return 1.0
        return float(current_vol / avg_vol)

    @classmethod
    def get_feature_snapshot(cls, df_5m: pd.DataFrame, df_15m: pd.DataFrame, 
                             india_vix: float, vix_history_5d: pd.Series,
                             df_nifty_daily: pd.DataFrame) -> Dict[str, float]:
        """
        Collects all 10 features.
        """
        snapshot = {
            "ADX_5m": cls.calculate_adx(df_5m),
            "ADX_15m": cls.calculate_adx(df_15m),
            "Choppiness_5m": cls.calculate_choppiness(df_5m),
            "Hurst_exponent": cls.calculate_hurst(df_5m['close']),
            "RV_ratio": cls.calculate_rv_ratio(df_5m),
            "VIX_level": float(india_vix),
            "VIX_slope": cls.calculate_vix_slope(vix_history_5d),
            "Nifty_ATR_pct": cls.calculate_atr_percentile(df_nifty_daily),
            "Range_ratio": cls.calculate_range_ratio(df_5m),
            "Volume_ratio": cls.calculate_volume_ratio(df_5m)
        }
        return snapshot
