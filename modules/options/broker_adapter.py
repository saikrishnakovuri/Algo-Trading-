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
            token = str(symbol_or_token)

        # Determine exchange. If it's a numeric token, we need to be careful.
        # Most index options tokens are in NFO.
        if str(symbol_or_token).isdigit() and len(str(symbol_or_token)) >= 5 and symbol_or_token not in self.tokens.values():
            # If it's a numeric token that isn't NIFTY/BANKNIFTY/VIX, it's likely NFO (Option/Future)
            exchange = "NFO"
        else:
            exchange = self.get_exchange(symbol_or_token)

        data = self.broker.get_market_data(exchange, symbol_or_token if not symbol_or_token.isdigit() else "", token)
        if data and data.get('status'):
            return data['data']['ltp']
        return 0.0

    async def async_get_ltp(self, symbol_or_token: str):
        """Asynchronously fetches LTP for a symbol or token."""
        # 1. Try hardcoded tokens
        token = self.tokens.get(symbol_or_token)

        # 2. Try ScripMaster lookup
        if not token:
            token = scrip_master.get_token(symbol_or_token)

        # 3. Fallback to input itself
        if not token:
            token = str(symbol_or_token)

        # Logic for determining exchange when only token is provided
        if str(symbol_or_token).isdigit() and len(str(symbol_or_token)) >= 5 and symbol_or_token not in self.tokens.values():
            exchange = "NFO"
        else:
            exchange = self.get_exchange(symbol_or_token)

        # Pass empty symbol if we only have token to avoid confusion in some broker APIs
        data = await self.broker.async_get_market_data(exchange, symbol_or_token if not symbol_or_token.isdigit() else "", token)
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
        """Fetches available expiries dynamically from Scrip Master."""
        from datetime import date
        from modules.options.scrip_master import scrip_master
        
        today = date.today().strftime('%Y-%m-%d')
        expiries = set()
        
        # ScripMaster data keys: (name, expiry, strike, option_type)
        for key in scrip_master._data.keys():
            if key[0] == symbol and key[1] >= today:
                expiries.add(key[1])
                
        sorted_expiries = sorted(list(expiries))
        
        # Fallback to hardcoded Thursdays if scrip_master is empty
        if not sorted_expiries:
            from datetime import timedelta
            td_today = date.today()
            for i in range(28):
                d = td_today + timedelta(days=i)
                if d.weekday() == 3: # Thursday
                    sorted_expiries.append(d.strftime('%Y-%m-%d'))
                    
        return sorted_expiries

    def get_full_option_chain(self, symbol: str):
        """Fetches current prices for all strikes in the chain using live tokens."""
        spot = self.get_ltp(symbol)
        df = fetch_option_chain(underlying_price=spot, use_nse_api=True)
        
        # ScripMaster mapping: symbol + strike + type -> token
        from modules.options.scrip_master import scrip_master
        
        # Dynamically format the nearest expiry
        expiries = self.get_expiry_list(symbol)
        if not expiries:
            return pd.DataFrame()
            
        expiry_str = expiries[0] # e.g. 2026-05-12
        d = datetime.strptime(expiry_str, "%Y-%m-%d")
        formatted_expiry = d.strftime("%d%b%y").upper() # 12MAY26
        
        rows = []
        for _, r in df.iterrows():
            strike = int(r['strike'])
            
            # Only fetch real LTP for strikes near ATM to avoid O(N) 40+ sec delays
            # +/- 300 points is enough for standard intraday index options
            is_near_atm = abs(strike - spot) <= 300
            
            # CE
            ce_symbol = f"{symbol}{formatted_expiry}{strike}CE"
            ce_token = scrip_master.get_token(ce_symbol)
            ce_ltp = self.get_ltp(ce_symbol) if (ce_token and is_near_atm) else 0.0
            
            rows.append({
                'strike': strike,
                'type': 'CE',
                'expiry': expiry_str,
                'token': ce_token,
                'ltp': ce_ltp,
                'oi': r['CE_OI'],
                'volume': r['CE_volume'],
                'delta': 0.5,
            })
            
            # PE
            pe_symbol = f"{symbol}{formatted_expiry}{strike}PE"
            pe_token = scrip_master.get_token(pe_symbol)
            pe_ltp = self.get_ltp(pe_symbol) if (pe_token and is_near_atm) else 0.0
            
            rows.append({
                'strike': strike,
                'type': 'PE',
                'expiry': expiry_str,
                'token': pe_token,
                'ltp': pe_ltp,
                'oi': r['PE_OI'],
                'volume': r['PE_volume'],
                'delta': -0.5,
            })
            
        return pd.DataFrame(rows)
