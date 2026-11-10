import yfinance as yf
import pandas as pd

class DataLayer:
    def __init__(self, symbol="^NSEI"):
        self.symbol = symbol

    def fetch_nifty_data(self, period="5d", interval="15m"):
        """
        Fetches NIFTY spot data. 
        In production, replace this with a broker API like Kite or Dhan.
        """
        try:
            data = yf.download(self.symbol, period=period, interval=interval)
            if data.empty:
                print(f"No data found for {self.symbol}")
                return None
            return data
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def fetch_option_chain_summary(self):
        """
        Placeholder for fetching Option Chain data.
        In a real scenario, use NSEPython or a Broker API.
        """
        # Returning mock data for demonstration
        return {
            "PCR": 0.85,
            "MaxPain": 22400,
            "CE_OI_Change": "High unwinding at 22500",
            "PE_OI_Change": "Strong buildup at 22300"
        }

    def get_multi_timeframe_data(self) -> dict:
        """Fetches NIFTY data for common intraday timeframes.

        Returns a dict with keys '1m', '5m', '15m' and pandas DataFrames or None.
        In production, replace with broker historical/candles API for reliability.
        """
        tfs = {}
        try:
            df1 = yf.download(self.symbol, period="7d", interval="1m")
            tfs['1m'] = df1 if (df1 is not None and not df1.empty) else None
        except Exception:
            tfs['1m'] = None

        try:
            df5 = yf.download(self.symbol, period="30d", interval="5m")
            tfs['5m'] = df5 if (df5 is not None and not df5.empty) else None
        except Exception:
            tfs['5m'] = None

        try:
            df15 = yf.download(self.symbol, period="60d", interval="15m")
            tfs['15m'] = df15 if (df15 is not None and not df15.empty) else None
        except Exception:
            tfs['15m'] = None

        return tfs
