import os
import time
import asyncio
import pyotp
import pandas as pd
from datetime import datetime, timedelta
from SmartApi import SmartConnect
from dotenv import load_dotenv

load_dotenv()
class AngelOneBroker:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AngelOneBroker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        self.api_key = os.getenv("ANGEL_API_KEY")
        self.client_id = os.getenv("ANGEL_CLIENT_ID")
        self.password = os.getenv("ANGEL_PASSWORD")
        self.totp_token = os.getenv("ANGEL_TOTP_TOKEN")
        self.smart_api = None
        self.auth_token = None
        # Rate Limiting State
        self.last_call_time = 0
        self.min_interval = 0.5 # Increased from 0.35 to avoid AB1021
        self._async_rate_lock = None
        self._initialized = True

    def login(self):
        if self.auth_token:
            print("Already logged in.")
            return True

        """Authenticates with Angel One using SmartApi and TOTP."""
        if not all([self.api_key, self.client_id, self.password, self.totp_token]):
            print("Missing Credentials! Ensure ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, and ANGEL_TOTP_TOKEN are in .env")
            return False
            
        try:
            self.smart_api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_token).now()
            data = self.smart_api.generateSession(self.client_id, self.password, totp)
            
            if data and data.get('status'):
                self.auth_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                print(f"Angel One Login Successful for {self.client_id}")
                return True
            else:
                msg = data.get('message') if data else "No response from API"
                print(f"Login Failed: {msg}")
                return False
        except Exception as e:
            print(f"Angel One Connection Error: {str(e)}")
            return False

    def _rate_limit(self):
        """Internal helper to ensure we don't spam the API."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

    async def async_rate_limit(self):
        """Async internal helper to ensure we don't spam the API without blocking the event loop."""
        import asyncio
        if self._async_rate_lock is None:
            self._async_rate_lock = asyncio.Lock()
            
        async with self._async_rate_lock:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call_time = time.time()

    async def async_get_market_data(self, exchange, tradingsymbol, symboltoken):
        """Asynchronously fetches real-time LTP for a specific token."""
        try:
            await self.async_rate_limit()
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.smart_api.ltpData, exchange, tradingsymbol, symboltoken)
        except Exception as e:
            print(f"Error fetching data for {tradingsymbol}: {e}")
            return None

    def get_market_data(self, exchange, tradingsymbol, symboltoken):
        """Fetches real-time LTP for a specific token."""
        try:
            self._rate_limit()
            return self.smart_api.ltpData(exchange, tradingsymbol, symboltoken)
        except Exception as e:
            print(f"Error fetching data for {tradingsymbol}: {e}")
            return None

    def _get_exchange(self, symbol):
        """Helper to determine correct exchange based on symbol naming convention."""
        # Options usually contain 'CE' or 'PE', indices/equities don't.
        # This logic should be robust enough for NIFTY/BANKNIFTY options.
        if "CE" in symbol or "PE" in symbol:
            return "NFO"
        return "NSE"

    def place_order(self, symbol, token, qty, side, order_type="LIMIT", price=0, stoploss=0):
        """Places an order with Angel One."""
        try:
            self._rate_limit()
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": side,
                "exchange": self._get_exchange(symbol),
                "ordertype": order_type,
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(price),
                "quantity": str(qty)
            }
            order_id = self.smart_api.placeOrder(order_params)
            print(f"Order Placed: {side} {qty} {symbol} at {price}. ID: {order_id}")
            return order_id
        except Exception as e:
            print(f"Order Placement Error: {e}")
            return None

    def place_bracket_order(self, symbol, token, qty, side, entry_price, sl_price, target_price, trailing_sl_points=0, order_tag="BOT_TRADE"):
        """
        Places a Bracket Order (ROBO) with Angel One.
        """
        try:
            self._rate_limit()
            # Angel One BO expects stoploss and squareoff as absolute point offsets from entry
            stoploss_delta = round(abs(entry_price - sl_price), 2)
            target_delta = round(abs(target_price - entry_price), 2)

            order_params = {
                "variety": "ROBO",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": side,
                "exchange": self._get_exchange(symbol),
                "ordertype": "LIMIT",
                "producttype": "BO",
                "duration": "DAY",
                "price": str(entry_price),
                "quantity": str(qty),
                "squareoff": str(target_delta),
                "stoploss": str(stoploss_delta),
                "trailingstoploss": str(trailing_sl_points),  # activate TSL for live mode
                "ordertag": order_tag
            }
            
            response = self.smart_api.placeOrder(order_params)
            print(f"BO Placed: {side} {qty} {symbol} at {entry_price}. SL: {sl_price} (+{stoploss_delta}), Tgt: {target_price} (+{target_delta}). ID: {response}")
            return response
        except Exception as e:
            print(f"BO Placement Error for {symbol}: {e}")
            return None

    def get_positions(self):
        """Retrieves active intraday positions."""
        try:
            self._rate_limit()
            return self.smart_api.position()
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None

    def get_historical_data(self, symbol, token, interval="ONE_MINUTE", days=2, from_date_str=None, to_date_str=None, exchange="NSE"):
        """Fetches historical OHLCV data for analysis with retry logic."""
        from datetime import datetime, timedelta
        max_retries = 3
        
        # Determine Exchange (Indices often need NSE, but some APIs might need NSE_INDEX)
        # NIFTY/BANKNIFTY tokens (99926000, 99926009) are officially on NSE exchange
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                if from_date_str and to_date_str:
                    from_date = from_date_str
                    to_date = to_date_str
                else:
                    to_date = datetime.now().strftime('%Y-%m-%d %H:%M')
                    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
                
                params = {
                    "exchange": exchange,
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": from_date,
                    "todate": to_date
                }
                
                response = self.smart_api.getCandleData(params)
                if response['status'] and response['data'] is not None:
                    df = pd.DataFrame(response['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    df.set_index('Timestamp', inplace=True)
                    return df
                else:
                    msg = response.get('message', 'Unknown error')
                    if "exceeding access rate" in str(msg).lower() or "Access denied" in str(msg):
                        wait = 5 * (attempt + 1)
                        print(f"Server Rate Limit for {symbol}. Waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    
                    # Fallback for Indices if first attempt fails
                    if exchange == "NSE" and symbol in ["NIFTY", "BANKNIFTY", "INDIA_VIX"]:
                        logger.info(f"Retrying {symbol} with NSE_INDEX exchange...")
                        exchange = "NSE" # Some versions use 'NSE' for equity and 'NSE' for index tokens
                        # If it failed once, maybe just a transient error, but let's try a small delay
                        time.sleep(1)
                        continue

                    if "AB1021" in str(msg) or "Too many" in str(msg):
                        wait = 2 ** attempt
                        print(f"Rate limited (AB1021) for {symbol}. Waiting {wait}s (Attempt {attempt+1}/{max_retries})...")
                        time.sleep(wait)
                        continue
                    print(f"API Error for {symbol}: {msg}")
                    return None
            except Exception as e:
                if "AB1021" in str(e) or "Too many" in str(e):
                    wait = 2 ** attempt
                    print(f"Exception Rate limit for {symbol}. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"Historical Data Exception for {symbol}: {e}")
                return None
        
        print(f"Failed to fetch data for {symbol} after {max_retries} attempts.")
        return None
