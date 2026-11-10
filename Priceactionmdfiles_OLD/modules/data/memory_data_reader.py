import pandas as pd
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from modules.websocket_manager import DirectWebSocketManager
from modules.broker_layer import AngelOneBroker

logger = logging.getLogger('live_trader')

class MemoryDataReader:
    """
    Local in-memory replacement for RedisDataReader.
    Maintains OHLCV data using WebSockets and initial API fetches.
    """
    def __init__(self, broker: AngelOneBroker):
        self.broker = broker
        self.ws_manager: Optional[DirectWebSocketManager] = None
        self.ohlc_data: Dict[str, pd.DataFrame] = {} # token -> 1m df
        self.ohlc_5m: Dict[str, pd.DataFrame] = {}   # token -> 5m df (PRE-CALCULATED)
        self.symbols_map: Dict[str, str] = {} # symbol_name -> token
        self.tier1_symbols: List[str] = []
        self.is_connected = True 
        self._lock = threading.Lock()

    def initialize_data(self, symbols_map: Dict[str, str], tier1_symbols: List[str] = None):
        """
        Initial fetch of historical data for all symbols.
        symbols_map: {symbol_name: token}
        """
        logger.info(f"Initializing in-memory data for {len(symbols_map)} symbols...")
        self.symbols_map = symbols_map
        self.tier1_symbols = tier1_symbols or []
        
        for symbol, token in symbols_map.items():
            # Initial placeholder for 5m
            with self._lock:
                self.ohlc_5m[token] = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            
            # Crucial: Only pre-load Tier 1 via API to avoid rate limits
            if symbol in self.tier1_symbols:
                try:
                    # Fetch 5 days of 1-minute data (ensures we have enough even after a weekend)
                    fetch_sym = symbol if symbol in ["NIFTY", "BANKNIFTY", "INDIA_VIX"] else f"{symbol}-EQ"
                    df = self.broker.get_historical_data(fetch_sym, token, interval="ONE_MINUTE", days=5)
                    if df is not None and not df.empty:
                        # Ensure naive timestamps for compatibility with local candle builder
                        df.index = df.index.tz_localize(None)
                        with self._lock:
                            self.ohlc_data[token] = df
                            # Pre-resample 5m
                            self.ohlc_5m[token] = df.resample('5min').agg({
                                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                            }).dropna()
                        logger.info(f"Loaded {len(df)} 1m bars for {symbol} (Tier 1)")
                    else:
                        logger.warning(f"Failed to load data for {symbol}")
                except Exception as e:
                    logger.error(f"Error loading {symbol}: {e}")
            else:
                # Tier 2/3: Start with empty DF, build live from WS
                with self._lock:
                    self.ohlc_data[token] = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

    def start_streaming(self, tokens: List[str]):
        """Starts the WebSocket feed."""
        self.ws_manager = DirectWebSocketManager(
            self.broker.api_key, 
            self.broker.client_id, 
            self.broker.auth_token, 
            self.broker.feed_token
        )
        self.ws_manager.on_reconnect_callback = self.trigger_gap_patch
        self.ws_manager.start(tokens)
        
        # Start background thread to build candles
        threading.Thread(target=self._candle_builder_loop, daemon=True).start()

    def trigger_gap_patch(self):
        """Fetches missing data from API after reconnection."""
        logger.info("Triggering Gap Patch for all symbols...")
        token_to_sym = {v: k for k, v in self.symbols_map.items()}
        
        for token, df in self.ohlc_data.items():
            try:
                if df.empty: continue
                last_ts = df.index[-1]
                now = datetime.now()
                
                if (now - last_ts).total_seconds() > 120:
                    symbol = token_to_sym.get(token, "UNKNOWN")
                    from_str = last_ts.strftime('%Y-%m-%d %H:%M')
                    to_str = now.strftime('%Y-%m-%d %H:%M')
                    
                    fetch_sym = symbol if symbol in ["NIFTY", "BANKNIFTY", "INDIA_VIX"] else f"{symbol}-EQ"
                    patch_df = self.broker.get_historical_data(fetch_sym, token, interval="ONE_MINUTE", from_date_str=from_str, to_date_str=to_str)
                    
                    if patch_df is not None and not patch_df.empty:
                        patch_df.index = patch_df.index.tz_localize(None)
                        with self._lock:
                            combined = pd.concat([self.ohlc_data[token], patch_df])
                            self.ohlc_data[token] = combined[~combined.index.duplicated(keep='last')].sort_index()
                            # Update 5m as well
                            self.ohlc_5m[token] = self.ohlc_data[token].resample('5min').agg({
                                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                            }).dropna()
            except Exception as e:
                logger.error(f"GAP_PATCH_ERROR for token {token}: {e}")

    def _candle_builder_loop(self):
        """Background thread to update OHLC data with live ticks."""
        while True:
            try:
                with self._lock:
                    for token, df in self.ohlc_data.items():
                        ltp = self.ws_manager.get_ltp(token)
                        if ltp:
                            now = datetime.now()
                            candle_ts = now.replace(second=0, microsecond=0)
                            
                            if candle_ts in df.index:
                                df.at[candle_ts, 'High'] = max(df.at[candle_ts, 'High'], ltp)
                                df.at[candle_ts, 'Low'] = min(df.at[candle_ts, 'Low'], ltp)
                                df.at[candle_ts, 'Close'] = ltp
                            else:
                                new_row = pd.DataFrame([{'Open': ltp, 'High': ltp, 'Low': ltp, 'Close': ltp, 'Volume': 0}], index=[candle_ts])
                                self.ohlc_data[token] = pd.concat([df, new_row])
                                if len(self.ohlc_data[token]) > 1000:
                                    self.ohlc_data[token] = self.ohlc_data[token].tail(1000)
                            
                            # INCREMENTAL 5m UPDATE (Avoid full resample)
                            c5_ts = candle_ts.replace(minute=(candle_ts.minute // 5) * 5)
                            df5 = self.ohlc_5m[token]
                            if not df5.empty and c5_ts in df5.index:
                                df5.at[c5_ts, 'High'] = max(df5.at[c5_ts, 'High'], ltp)
                                df5.at[c5_ts, 'Low'] = min(df5.at[c5_ts, 'Low'], ltp)
                                df5.at[c5_ts, 'Close'] = ltp
                            else:
                                new_5m = pd.DataFrame([{'Open': ltp, 'High': ltp, 'Low': ltp, 'Close': ltp, 'Volume': 0}], index=[c5_ts])
                                self.ohlc_5m[token] = pd.concat([df5, new_5m])
                                if len(self.ohlc_5m[token]) > 500:
                                    self.ohlc_5m[token] = self.ohlc_5m[token].tail(500)
            except Exception as e:
                logger.error(f"CANDLE_BUILDER_ERROR: {e}")
            time.sleep(1)

    def get_5m_candles(self, token: str, count: int = 100) -> Optional[pd.DataFrame]:
        """Low-latency fetch of pre-calculated 5m candles."""
        with self._lock:
            df = self.ohlc_5m.get(token)
            if df is None or df.empty:
                return None
            df = df.tail(count).copy()
            df.columns = [c.lower() for c in df.columns]
            if df.index.name:
                df.index.name = df.index.name.lower()
            return df

    def get_live_price(self, token: str) -> Optional[dict]:
        ltp = self.ws_manager.get_ltp(token) if self.ws_manager else None
        if ltp:
            return {'ltp': ltp, 'v': 0, 'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        return None

    def get_live_candle(self, token: str, timeframe: str = '5m') -> Optional[dict]:
        df = self.get_5m_candles(token, 1)
        if df is not None and not df.empty:
            return {
                'open': float(df['open'].iloc[-1]),
                'high': float(df['high'].iloc[-1]),
                'low': float(df['low'].iloc[-1]),
                'close': float(df['close'].iloc[-1]),
                'volume': int(df['volume'].iloc[-1])
            }
        return None

    def get_candle_count(self, token: str, timeframe: str = '5m') -> int:
        df = self.get_5m_candles(token)
        return len(df) if df is not None else 0

    def is_data_fresh(self, token: str) -> bool:
        return self.ws_manager.get_ltp(token) is not None
