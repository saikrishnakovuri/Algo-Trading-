import os
import json
import time
import logging
import signal
import sys
import redis
import threading
from datetime import datetime
from typing import List, Dict, Optional
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from modules.broker_layer import AngelOneBroker

# Configuration
LOG_FILE = "logs/websocket_feed.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("websocket_feed")

# REQ 26-3: WebSocket Integrity Log
WS_INTEGRITY_LOG = "logs/ws_integrity.log"

def log_ws_integrity(event: str):
    with open(WS_INTEGRITY_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {event}\n")

class WebSocketPool:
    def __init__(self, api_key: str, client_id: str, auth_token: str, feed_token: str):
        # ... (rest of init)
        self.api_key = api_key
        self.client_id = client_id
        self.auth_token = auth_token
        self.feed_token = feed_token
        
        if os.getenv("SKIP_REDIS_CHECK") == "1":
            logger.info("DRY RUN: Using Redis Stub")
            self.r = type('RedisStub', (object,), {
                'ping': lambda self: True,
                'publish': lambda self, c, m: 0,
                'hset': lambda self, k, mapping=None: True
            })()
        else:
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Redis Connection Failed: {e}")
                sys.exit(1)

        self.connections: Dict[int, SmartWebSocketV2] = {}
        self.token_to_exchange: Dict[str, str] = {} # token -> 'NSE' or 'MCX'
        self.total_ticks = 0
        self.is_running = True

    def on_data(self, ws, message):
        try:
            token = message.get('token')
            ltp = message.get('last_traded_price')
            volume = message.get('v')
            timestamp = message.get('exchange_timestamp')
            
            exchange = self.token_to_exchange.get(token, 'NSE')

            if token and ltp:
                tick_data = {
                    't': token,
                    'lp': ltp / 100,
                    'v': volume if volume is not None else 0,
                    'ts': timestamp if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                payload = json.dumps(tick_data)
                # Channel: ticks:EXCHANGE:token
                self.r.publish(f"ticks:{exchange}:{token}", payload)
                # Key: latest_tick:EXCHANGE:token
                self.r.hset(f"latest_tick:{exchange}:{token}", mapping=tick_data)
                self.total_ticks += 1
        except Exception as e:
            logger.error(f"Error processing tick: {e}")

    def _on_open(self, ws):
        logger.info("WebSocket Connection Opened")
        log_ws_integrity("CONNECTED")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket Error: {error}")
        log_ws_integrity(f"ERROR: {error}")

    def _on_close(self, ws):
        logger.warning("WebSocket Connection Closed")
        log_ws_integrity("DISCONNECTED")

    def start_streaming(self, nse_tokens: List[str], mcx_tokens: List[str]):
        """
        Starts connections:
        - NSE T1/T2: Mode 3 (NSE tokens)
        - NSE T3: Mode 1 (LTP only)
        - MCX: Mode 3 (Full)
        """
        # Map tokens to exchange for callback
        for t in nse_tokens: self.token_to_exchange[t] = 'NSE'
        for t in mcx_tokens: self.token_to_exchange[t] = 'MCX'

        # Connection 1: NSE Tier 1 & 2 (Mode 3)
        # Limit 1000 per conn. For simplicity, we just chunk them.
        self._start_conn(1, 1, nse_tokens[:1000], mode=3)
        
        # Connection 2: NSE Tier 3 (Mode 1)
        if len(nse_tokens) > 1000:
            self._start_conn(2, 1, nse_tokens[1000:2000], mode=1)
            
        # Connection 3: MCX (Mode 3)
        if mcx_tokens:
            self._start_conn(3, 5, mcx_tokens, mode=3)

        threading.Thread(target=self._stats_loop, daemon=True).start()

    def _start_conn(self, conn_id: int, exch_type: int, tokens: List[str], mode: int):
        if not tokens: return
        logger.info(f"Starting WS Conn {conn_id} for Exch {exch_type} ({len(tokens)} tokens, mode {mode})")
        
        sws = SmartWebSocketV2(self.auth_token, self.api_key, self.client_id, self.feed_token)
        sws.on_open = self._on_open
        sws.on_data = self.on_data
        sws.on_error = self._on_error
        sws.on_close = self._on_close
        
        subscription_list = [{"exchangeType": exch_type, "tokens": tokens}]
        
        t = threading.Thread(target=self._run_conn, args=(sws, conn_id, mode, subscription_list))
        t.daemon = True
        t.start()
        self.connections[conn_id] = sws

    def _run_conn(self, sws, conn_id, mode, subscription_list):
        try:
            sws.connect()
            sws.subscribe(f"pool_{conn_id}", mode, subscription_list)
        except Exception as e:
            logger.error(f"Conn {conn_id} failed: {e}")

    def _stats_loop(self):
        while self.is_running:
            time.sleep(60)
            logger.info(f"WS_POOL: {self.total_ticks/60:.1f} tps | {len(self.connections)} active")
            self.total_ticks = 0

    def stop(self):
        self.is_running = False
        for s in self.connections.values():
            try: s.close()
            except: pass

def run_feed():
    if os.getenv("SKIP_REDIS_CHECK") == "1":
        from modules.dry_run_stubs import AngelOneBrokerStub
        broker = AngelOneBrokerStub()
        # Stub session
        session = {'status': True, 'data': {'jwtToken': 'MOCK_JWT', 'feedToken': 'MOCK_FEED'}}
    else:
        broker = AngelOneBroker()
        if not broker.login(): return

        import pyotp
        from SmartApi import SmartConnect
        smart_api = SmartConnect(api_key=broker.api_key)
        totp = pyotp.TOTP(broker.totp_token).now()
        session = smart_api.generateSession(broker.client_id, broker.password, totp)
    
    if not session.get('status'): return
    
    auth_token = session['data']['jwtToken']
    feed_token = session['data']['feedToken']

    # Load Tiers
    try:
        import yaml
        with open("config/universe_full.yaml", "r") as f:
            universe = yaml.safe_load(f)['universe']
        with open("broker_tokens_full.json", "r") as f:
            token_map = json.load(f)

        nse_tokens = []
        # Group NSE Tier 1 and 2 first for Mode 3
        for sym in universe['tiers'].get('TIER_1', []) + universe['tiers'].get('TIER_2', []) + universe['tiers'].get('TIER_3', []):
            token = token_map.get(f"{sym}-EQ")
            if token: nse_tokens.append(str(token))
            
        mcx_tokens = []
        for key, data in universe.get('mcx', {}).items():
            mcx_tokens.append(str(data['token']))
            
        logger.info(f"Loaded: NSE={len(nse_tokens)}, MCX={len(mcx_tokens)}")
    except Exception as e:
        logger.error(f"Failed to load universe: {e}")
        return

    pool = WebSocketPool(broker.api_key, broker.client_id, auth_token, feed_token)
    def signal_handler(sig, frame):
        pool.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    pool.start_streaming(nse_tokens, mcx_tokens)
    while True: time.sleep(1)

if __name__ == "__main__":
    run_feed()
