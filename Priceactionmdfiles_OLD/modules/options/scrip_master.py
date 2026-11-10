import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("ScripMaster")

class ScripMaster:
    _instance = None
    _data = {} # (name, expiry, strike, type) -> token
    _symbol_map = {} # symbol -> token
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScripMaster, cls).__new__(cls)
        return cls._instance

    def initialize(self, file_path='scrip_master.json'):
        if self._initialized:
            return
        
        if not os.path.exists(file_path):
            logger.error(f"Scrip master file not found: {file_path}")
            return

        logger.info(f"Loading scrip master from {file_path}...")
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
            
            for item in raw_data:
                token = item.get('token')
                symbol = item.get('symbol')
                name = item.get('name')
                exch = item.get('exch_seg')
                
                if not token or not symbol:
                    continue
                
                # Index by exact symbol
                self._symbol_map[symbol] = {
                    'token': token,
                    'exch': exch,
                    'symbol': symbol,
                    'name': name
                }
                
                # For options, index by components
                if exch == 'NFO' and item.get('expiry'):
                    try:
                        # Convert expiry from DDMMMYYYY to YYYY-MM-DD
                        expiry_raw = item.get('expiry') 
                        expiry_dt = datetime.strptime(expiry_raw, '%d%b%Y')
                        expiry_iso = expiry_dt.strftime('%Y-%m-%d')
                        
                        raw_strike = float(item.get('strike', 0))
                        strike = raw_strike
                        if strike >= 100000: 
                            strike = strike / 100.0
                        
                        option_type = 'CE' if symbol.endswith('CE') else 'PE' if symbol.endswith('PE') else 'FUT'
                        
                        # Store strike as float for better matching
                        key = (name.upper(), expiry_iso, float(strike), option_type)
                        self._data[key] = token
                        
                        if name == 'BANKNIFTY' and '2026-05' in expiry_iso:
                            # logger.debug(f"Indexed: {key} -> {token}")
                            pass
                    except Exception as e:
                        continue
            
            self._initialized = True
            logger.info(f"Scrip Master initialized with {len(self._symbol_map)} symbols.")
        except Exception as e:
            logger.error(f"Failed to initialize Scrip Master: {e}")

    def get_token(self, symbol):
        res = self._symbol_map.get(symbol)
        return res['token'] if res else None

    def lookup_option(self, name, expiry, strike, option_type):
        """
        Lookup token by components.
        expiry: YYYY-MM-DD
        strike: int/float
        option_type: 'CE' or 'PE'
        """
        key = (name.upper(), expiry, float(strike), option_type.upper())
        return self._data.get(key)

    def get_details(self, symbol):
        return self._symbol_map.get(symbol)

# Global Instance
scrip_master = ScripMaster()
