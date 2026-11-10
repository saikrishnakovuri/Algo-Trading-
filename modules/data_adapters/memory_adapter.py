from .base_adapter import DataAdapter, InstrumentInfo, MarketHoursConfig, AdapterError
import pandas as pd

class MemoryAdapter(DataAdapter):
    """Wraps existing MemoryDataReader/Backtest engine."""
    def __init__(self, cfg):
        # Implementation depends on existing MemoryDataReader
        self.name = "memory"
    
    def get_bars(self, symbol, timeframe="5m", count=200):
        # Placeholder for backtest engine integration
        return pd.DataFrame()

    def get_live_price(self, symbol):
        return 0.0

    def get_instrument_info(self, symbol):
        return InstrumentInfo(symbol, symbol, "INDEX", 0.05, 65, "INR", False)

    def get_market_hours(self):
        from datetime import time
        return MarketHoursConfig(time(0,0), time(23,59), time(0,0), time(23,59), time(23,59), "Asia/Kolkata", True, ["Mon","Tue","Wed","Thu","Fri"])

    def health_check(self):
        return {"status": "OK", "details": "Backtest ready"}
