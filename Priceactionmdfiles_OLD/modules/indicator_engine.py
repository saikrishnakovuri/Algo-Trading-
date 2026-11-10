import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    ta = None

class IndicatorEngine:
    @staticmethod
    def calculate_rsi(df, period=14):
        if ta: return ta.rsi(df['close'], length=period)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_atr(df, period=14):
        if ta: return ta.atr(df['high'], df['low'], df['close'], length=period)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean()

    @staticmethod
    def add_indicators(df):
        if df is None or df.empty: return None
        if ta:
            df['RSI'] = ta.rsi(df['close'], length=14)
            df['EMA_20'] = ta.ema(df['close'], length=20)
            df['EMA_50'] = ta.ema(df['close'], length=50)
            df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        else:
            df['RSI'] = IndicatorEngine.calculate_rsi(df)
            df['EMA_20'] = df['close'].ewm(span=20).mean()
            df['EMA_50'] = df['close'].ewm(span=50).mean()
            df['VWAP'] = df['close'] # Stub
        return df

    @staticmethod
    def get_trend(df):
        """
        Identifies trend direction based on EMAs.
        """
        last_row = df.iloc[-1]

        def _to_float(v):
            import numpy as _np
            try:
                if v is None:
                    return float('nan')

                # pandas Series / Index: take last element
                if isinstance(v, (pd.Series, pd.Index)):
                    try:
                        val = v.iloc[-1]
                    except Exception:
                        try:
                            arr = _np.asarray(v)
                            if arr.size == 0:
                                return float('nan')
                            val = arr.ravel()[-1]
                        except Exception:
                            return float('nan')

                    try:
                        return float(val.item()) if hasattr(val, 'item') else float(val)
                    except Exception:
                        try:
                            return float(_np.asarray(val).ravel()[-1])
                        except Exception:
                            return float('nan')

                # numpy array or scalar or plain python scalar
                try:
                    arr = _np.asarray(v)
                    if arr.size == 0:
                        return float('nan')
                    val = arr.ravel()[-1]
                    return float(val.item()) if hasattr(val, 'item') else float(val)
                except Exception:
                    return float('nan')
            except Exception:
                return float('nan')

        e20 = _to_float(last_row.get('EMA_20'))
        e50 = _to_float(last_row.get('EMA_50'))

        if pd.isna(e20) or pd.isna(e50):
            return "Sideways"

        if e20 > e50:
            return "Uptrend"
        elif e20 < e50:
            return "Downtrend"
        else:
            return "Sideways"
