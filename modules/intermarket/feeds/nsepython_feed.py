import pandas as pd
from typing import Dict, Any, Optional
from nsepython import nse_get_index_quote, nse_get_advances_declines
from modules.intermarket.feeds.base import CrossAssetFeed

class NSEPythonFeed(CrossAssetFeed):
    """
    Direct NSE data feed using nsepython for VIX and Breadth.
    """
    
    def get_latest_data(self, symbol: str, backtest_mode: bool = False) -> Dict[str, Any]:
        """
        Specialized fetch for India VIX or Index spot.
        """
        try:
            # Normalize symbols for nsepython
            if "VIX" in symbol.upper():
                target = "INDIA VIX"
            elif "NIFTY 50" in symbol.upper() or symbol.upper() == "NIFTY":
                target = "NIFTY 50"
            elif "BANK" in symbol.upper():
                target = "NIFTY BANK"
            else:
                target = symbol
                
            quote = nse_get_index_quote(target)
            if not quote or 'lastPrice' not in quote:
                if not backtest_mode:
                    print(f"⚠️ NSE Fetch Empty for {target}")
                return {}
                
            return {
                'close': float(quote.get('lastPrice', 0)),
                'open': float(quote.get('open', 0)),
                'session_return': float(quote.get('pChange', 0.0)) / 100
            }
        except Exception as e:
            if not backtest_mode:
                print(f"❌ NSE Fetch Error for {symbol}: {e}")
            return {}

    def get_market_breadth(self) -> Dict[str, Any]:
        """
        Fetches market-wide advances/declines.
        """
        try:
            data = nse_get_advances_declines()
            # Find NIFTY 50 or NIFTY 200 row
            n200 = next((item for item in data if item["index"] == "NIFTY 200"), None)
            if n200:
                adv = int(n200['advances'])
                dec = int(n200['declines'])
                return {
                    'advances': adv,
                    'declines': dec,
                    'adr': adv / dec if dec > 0 else adv
                }
        except Exception:
            pass
        return {'advances': 0, 'declines': 0, 'adr': 1.0}

    def get_history(self, symbol: str, interval: str, count: int) -> pd.DataFrame:
        return pd.DataFrame()
