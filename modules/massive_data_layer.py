import os
import yfinance as yf
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

class MassiveDataLayer:
    """
    Handles bulk fetching of data for 1500+ stocks and resampling into multiple timeframes.
    """
    def __init__(self, symbols: List[str], data_dir: str = "data/nifty200"):
        self.symbols = [s.strip() + ".NS" for s in symbols]
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def fetch_1m_data(self, symbol: str, period: str = "7d") -> pd.DataFrame:
        """Fetch 1m data for a single symbol."""
        try:
            # yfinance 1m data is limited to max 7 days
            df = yf.download(symbol, period=period, interval="1m", progress=False)
            if df is not None and not df.empty:
                # Handle MultiIndex columns if yfinance returns them
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # Ensure we have the standard OHLCV columns
                cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df[cols]
                
                # Save to local CSV for caching
                file_path = os.path.join(self.data_dir, f"{symbol.replace('.NS', '')}_1m.csv")
                df.to_csv(file_path)
                return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()

    def bulk_fetch_1m(self, max_workers: int = 10):
        """Fetch 1m data for all symbols using threading."""
        print(f"🚀 Starting bulk fetch for {len(self.symbols)} symbols...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(self.fetch_1m_data, self.symbols))
        print("✅ Bulk fetch complete.")

    def fetch_angel_data(self, symbol: str, token: str, days: int = 30):
        """
        P1.6: Fetch high-quality historical 1m data via Angel One.
        Note: Requires active ANGEL API session.
        """
        from modules.broker_layer import AngelOneBroker
        broker = AngelOneBroker()
        if not broker.login():
            return None
        
        print(f"📡 Fetching {days} days of 1m data for {symbol} via Angel One...")
        df = broker.get_historical_data(symbol, token, interval="ONE_MINUTE", days=days)
        
        if df is not None and not df.empty:
            file_path = os.path.join(self.data_dir, f"{symbol.replace('-EQ', '')}_1m.csv")
            df.to_csv(file_path)
            print(f"✅ Data for {symbol} saved to {file_path}")
            return df
        return None

    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample 1m data into other timeframes (3m, 5m, 15m, 1h, etc.)
        timeframe: pandas frequency string (e.g. '3min', '5min', '15min', '1h')
        """
        if df.empty:
            return df
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        logic = {
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }
        # Handle cases where columns might be multi-index (yf sometimes does this)
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten or just take the relevant level if needed
            # For simplicity, we assume standard OHLCV
            pass

        return df.resample(timeframe).apply(logic).dropna()

    def get_status_report(self) -> str:
        """Generates a summary of what data we have stored locally."""
        files = os.listdir(self.data_dir)
        stock_count = len([f for f in files if f.endswith("_1m.csv")])
        
        report = f"--- DATA STATUS REPORT ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n"
        report += f"Total Nifty 200 Stocks Cached (1m): {stock_count}\n"
        report += f"Storage Directory: {self.data_dir}\n"
        report += f"Available Timeframes (via Resampling): 1m, 3m, 5m, 10m, 15m, 30m, 1h, 1d\n"
        
        if stock_count > 0:
            sample_file = [f for f in files if f.endswith("_1m.csv")][0]
            df_sample = pd.read_csv(os.path.join(self.data_dir, sample_file))
            if not df_sample.empty:
                start_date = df_sample.iloc[0]['Datetime'] if 'Datetime' in df_sample.columns else "N/A"
                end_date = df_sample.iloc[-1]['Datetime'] if 'Datetime' in df_sample.columns else "N/A"
                report += f"Data Range (Sample): {start_date} to {end_date}\n"
        
        return report
