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
        except Exception as e:
            logger.error(f"WS_DATA_ERROR: {e}")

    def on_open(self, ws):
        logger.info("WebSocket Connection Opened")
        self.reconnect_attempts = 0
        if self.tokens:
            subscription_list = [{"exchangeType": 1, "tokens": self.tokens}]
            self.sws.subscribe("bot_feed", 1, subscription_list)
            logger.info(f"Subscribed to {len(self.tokens)} tokens on open.")

    def on_error(self, ws, error):
        logger.error(f"WebSocket Error: {error}")

    def on_close(self, ws):
        logger.warning("WebSocket Connection Closed")
        if self.is_running:
            self._handle_reconnect()

    def _handle_reconnect(self):
        """Exponential backoff reconnection logic."""
        if not self.is_running: return
        
        self.reconnect_attempts += 1
        backoff = min(2 ** self.reconnect_attempts, self.max_reconnect_backoff)
        logger.info(f"Attempting reconnection in {backoff}s (Attempt {self.reconnect_attempts})...")
        
        time.sleep(backoff)
        try:
            self.sws.connect()
            if self.on_reconnect_callback:
                self.on_reconnect_callback()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            self._handle_reconnect()

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
