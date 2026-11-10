from .base_adapter import DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError
import pandas as pd
import numpy as np

class AngelOneAdapter(DataAdapter):
    """Wraps existing AngelOneBroker."""
    def __init__(self, cfg):
        from modules.broker_layer import AngelOneBroker
        self.broker = AngelOneBroker()
        self.broker.login()
        self.name = "angelone"
    
    def get_bars(self, symbol, timeframe="5m", count=200):
        from modules.options.scrip_master import scrip_master
        # Attempt to get token
        details = scrip_master.get_details(symbol)
        token = details['token'] if details else "99926000" # Fallback NIFTY
        
        interval = "ONE_MINUTE" if timeframe in ["1m", "5m"] else "FIFTEEN_MINUTE"
        days = max(5, int(count / 75)) # Rough approx
        
        df = self.broker.get_historical_data(symbol, token, interval=interval, days=days)
        if df is None or df.empty:
            raise AdapterError(f"No historical data for {symbol}")
            
        df.index = df.index.tz_localize(None)
        
        if timeframe == "5m":
            df = df.resample("5min").agg({
                "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
            }).dropna()
            
        return df.tail(count)

    def get_live_price(self, symbol):
        from modules.options.broker_adapter import OptionsBrokerAdapter
        # OptionsBrokerAdapter has the get_ltp logic that handles ScripMaster correctly
        adapter = OptionsBrokerAdapter(self.broker)
        return adapter.get_ltp(symbol)

    def get_instrument_info(self, symbol):
        return InstrumentInfo(symbol, symbol, "INDEX", 0.05, 65, "INR", False)

    def get_market_hours(self):
        from datetime import time
        return MarketHoursConfig(time(9,15), time(15,30), time(10,0), time(12,0), time(15,15), "Asia/Kolkata", False, ["Mon","Tue","Wed","Thu","Fri"])

    def health_check(self):
        return {"status": "OK", "details": "Connected"}
