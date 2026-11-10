import os
import json
import time
import logging
import threading
from typing import List, Dict, Optional
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from modules.broker_layer import AngelOneBroker

logger = logging.getLogger('live_trader')

class DirectWebSocketManager:
    """
    Manages a WebSocket connection and maintains an in-memory cache of LTP.
    Avoids the need for Redis for simpler setups.
    """
    def __init__(self, api_key: str, client_id: str, auth_token: str, feed_token: str):
        self.api_key = api_key
        self.client_id = client_id
        self.auth_token = auth_token
        self.feed_token = feed_token
        
        self.sws: Optional[SmartWebSocketV2] = None
        self.ltp_cache: Dict[str, float] = {} # token -> last price
        self.is_running = False
        self.tokens: List[str] = []
        self.reconnect_attempts = 0
        self.max_reconnect_backoff = 60 # seconds
        self._lock = threading.Lock()
        self.on_reconnect_callback = None

    def on_data(self, ws, message):
        try:
            token = message.get('token')
            ltp = message.get('last_traded_price')
            if token and ltp:
                with self._lock:
                    self.ltp_cache[token] = ltp / 100.0
                # Periodic debug log to avoid flooding
                if time.time() % 10 < 1:
                    logger.debug(f"WS_TICK | {token} | {ltp/100.0}")
        except Exception as e:
            logger.error(f"WS_DATA_ERROR: {e}")

    def on_open(self, ws):
        logger.info("WebSocket Connection Opened")
        self.reconnect_attempts = 0
        if self.tokens:
            # Separate NSE (equities/indices) and NFO (options)
            # Typically, NSE Cash tokens are < 50000, while NFO are > 50000 or have different ranges.
            # A more robust check: tokens from our list that don't match index IDs are checked by numeric value.
            nse_tokens = []
            nfo_tokens = []
            for t in self.tokens:
                if t in ["99926000", "99926009", "99926017"]:
                    nse_tokens.append(t)
                elif t.isdigit() and int(t) < 30000: # Most NSE stocks are in this range
                    nse_tokens.append(t)
                else:
                    nfo_tokens.append(t)
            
            subscription_list = []
            if nse_tokens:
                subscription_list.append({"exchangeType": 1, "tokens": nse_tokens})
            if nfo_tokens:
                subscription_list.append({"exchangeType": 2, "tokens": nfo_tokens})
                
            self.sws.subscribe("bot_feed", 1, subscription_list)
            logger.info(f"Subscribed to {len(self.tokens)} tokens on open (NSE: {len(nse_tokens)}, NFO: {len(nfo_tokens)}).")

    def on_error(self, ws, error):
        logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws):
        logger.warning("WebSocket Connection Closed")
        if self.is_running:
            self._handle_reconnect()

    def _handle_reconnect(self):
        """Spawns an iterative reconnection loop to avoid blocking and recursion."""
        if not self.is_running: return
        threading.Thread(target=self._reconnect_loop, daemon=True).start()
        
    def _reconnect_loop(self):
        while self.is_running:
            self.reconnect_attempts += 1
            backoff = min(2 ** self.reconnect_attempts, self.max_reconnect_backoff)
            logger.info(f"Attempting reconnection in {backoff}s (Attempt {self.reconnect_attempts})...")
            
            time.sleep(backoff)
            if not self.is_running: break
            try:
                self.sws.connect()
                if self.on_reconnect_callback:
                    self.on_reconnect_callback()
                break # Break out of loop on successful connect
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                # Loop will naturally continue to the next attempt

    def start(self, tokens: List[str]):
        """Starts the WebSocket in a background thread."""
        if not tokens: return
        self.tokens = tokens
        
        self.sws = SmartWebSocketV2(self.auth_token, self.api_key, self.client_id, self.feed_token)
        self.sws.on_open = self.on_open
        self.sws.on_data = self.on_data
        self.sws.on_error = self.on_error
        self.sws.on_close = self.on_close
        
        def run_ws():
            self.is_running = True
            try:
                self.sws.connect()
            except Exception as e:
                logger.error(f"WS_THREAD_ERROR: {e}")
                self._handle_reconnect()

        t = threading.Thread(target=run_ws, daemon=True)
        t.start()
        logger.info(f"WebSocket manager thread started for {len(tokens)} tokens.")


    def get_ltp(self, token: str) -> Optional[float]:
        with self._lock:
            return self.ltp_cache.get(token)

    def stop(self):
        self.is_running = False
        if self.sws:
            try: self.sws.close()
            except: pass
