import logging
import pandas as pd
from datetime import datetime
from modules.broker_layer import AngelOneBroker
from modules.option_chain import fetch_option_chain, calculate_pcr

from modules.options.scrip_master import scrip_master

logger = logging.getLogger("OptionsBrokerAdapter")

class OptionsBrokerAdapter:
    """
    Adapter to bridge AngelOneBroker with Options Strategy requirements.
    Provides methods for VIX, PCR, and Option Chain data.
    """
    def __init__(self, broker: AngelOneBroker):
        self.broker = broker
        # Common Index Tokens (NSE)
        self.tokens = {
            "NIFTY": "99926000",
            "BANKNIFTY": "99926009",
            "INDIA_VIX": "99926017"
        }

    def login(self):
        return self.broker.login()

    def get_exchange(self, symbol: str) -> str:
        # Check ScripMaster first
        details = scrip_master.get_details(symbol)
        if details:
            return details['exch']

        symbol_upper = symbol.upper()
        # VIX is strictly NSE
        if "VIX" in symbol_upper:
            return "NSE"
        # Options always go to NFO
        if symbol_upper.endswith("CE") or symbol_upper.endswith("PE") or "_" in symbol_upper:
            return "NFO"
        # Futures go to NFO
        if "FUT" in symbol_upper:
            return "NFO"
        # Index spot goes to NSE
        if symbol_upper in ["NIFTY", "BANKNIFTY", "NIFTY50", "FINNIFTY", "MIDCPNIFTY"]:
            return "NSE"
        # All equity stocks go to NSE
        return "NSE"

    def get_ltp(self, symbol_or_token: str):
        """Fetches LTP for a symbol or token."""
        # 1. Try hardcoded tokens
        token = self.tokens.get(symbol_or_token)
        
        # 2. Try ScripMaster lookup
        if not token:
            token = scrip_master.get_token(symbol_or_token)
            
        # 3. Fallback to input itself
        if not token:
            token = symbol_or_token
            
        exchange = self.get_exchange(symbol_or_token)

        data = self.broker.get_market_data(exchange, symbol_or_token, token)
        if data and data.get('status'):
            return data['data']['ltp']
        return 0.0

    def get_vix(self):
        """Fetches current India VIX level."""
        return self.get_ltp("INDIA_VIX")

    def get_pcr(self, symbol: str):
        """Calculates current PCR using simulated or real option chain."""
        # For now, we use the simulated/NSE fetcher from modules.option_chain
        spot = self.get_ltp(symbol)
        df = fetch_option_chain(underlying_price=spot, use_nse_api=True)
        return calculate_pcr(df)

    def get_option_chain_oi(self, symbol: str):
        """Fetches OI and Delta OI for the nearest strikes."""
        spot = self.get_ltp(symbol)
        df = fetch_option_chain(underlying_price=spot, use_nse_api=True)
        
        # Format for signal_adapter: {strike: {'ce_oi': X, 'pe_oi': Y, 'ce_oi_change': Z, 'pe_oi_change': W}}
        oi_data = {}
        # Get 5 strikes around ATM
        step = 100 if symbol == "BANKNIFTY" else 50
        atm = int(round(spot / step) * step)
        relevant_strikes = range(atm - 2*step, atm + 3*step, step)
        
        for strike in relevant_strikes:
            row = df[df['strike'] == strike]
            if not row.empty:
                r = row.iloc[0]
                oi_data[strike] = {
                    'ce_oi': r['CE_OI'],
                    'pe_oi': r['PE_OI'],
                    'ce_oi_change': r['CE_change'],
                    'pe_oi_change': r['PE_change']
                }
        return oi_data

    def get_expiry_list(self, symbol: str):
        """Placeholder: In live, this would fetch from Angel API or Scrip Master."""
        # For now, return a few upcoming Thursdays
        from datetime import date, timedelta
        today = date.today()
        # Find next 4 Thursdays
        expiries = []
        for i in range(28):
            d = today + timedelta(days=i)
            if d.weekday() == 3: # Thursday
                expiries.append(d.strftime('%Y-%m-%d'))
        return expiries

    def get_full_option_chain(self, symbol: str):
        """Fetches current prices and greeks for all strikes in the chain."""
        # This is complex in live as it requires multiple LTP calls or WebSocket.
        # For now, return a mock DataFrame that selectors can use.
        spot = self.get_ltp(symbol)
        df = fetch_option_chain(underlying_price=spot, use_nse_api=True)
        # Add mock Greeks and Expiry (assuming nearest)
        expiries = self.get_expiry_list(symbol)
        df['expiry'] = expiries[0]
        # Signal adapter expects 'type', 'ltp', etc.
        # OptionChain df has CE_OI, PE_OI... we need to melt it or handle it.
        
        rows = []
        for _, r in df.iterrows():
            # CE
            rows.append({
                'strike': r['strike'],
                'type': 'CE',
                'expiry': expiries[0],
                'ltp': spot * 0.008, # Mock premium ~150-200
                'bid': (spot * 0.008) - 0.5,
                'ask': (spot * 0.008) + 0.5,
                'oi': 1000000, # Mock high OI
                'volume': 500000, # Mock high volume
                'delta': 0.5,
                'theta': -10.0
            })
            # PE
            rows.append({
                'strike': r['strike'],
                'type': 'PE',
                'expiry': expiries[0],
                'ltp': spot * 0.008,
                'bid': (spot * 0.008) - 0.5,
                'ask': (spot * 0.008) + 0.5,
                'oi': 1000000,
                'volume': 500000,
                'delta': -0.5,
                'theta': -10.0
            })
        return pd.DataFrame(rows)
