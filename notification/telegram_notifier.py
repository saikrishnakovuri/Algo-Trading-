import requests
import time
import threading
import queue
from collections import deque
from notification.config import TELEGRAM_URL, CHAT_ID
from notification.formatter import format_trade_message
from utils.logger import get_logger

logger = get_logger("telegram_notifier")

class TelegramNotifier:
    """
    Optimized Telegram Notifier:
    - Async background queue (via threading)
    - Rate limiting (max 20 msgs / min)
    - Message deduplication
    - Retries with backoff
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(TelegramNotifier, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, retries=3, rate_limit_per_min=20):
        if self._initialized: return
        
        self.retries = retries
        self.rate_limit_per_min = rate_limit_per_min
        self.msg_queue = queue.Queue()
        self.sent_messages = deque(maxlen=rate_limit_per_min) # track timestamps
        self.seen_hashes = deque(maxlen=50) # simple deduplication
        
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        self._initialized = True
        logger.info("TelegramNotifier initialized with background worker")

    def _process_queue(self):
        while True:
            try:
                msg = self.msg_queue.get()
                if msg is None: break
                
                self._throttle()
                self._send_raw(msg)
                self.msg_queue.task_done()
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(1)

    def _throttle(self):
        """Enforces rate limit."""
        now = time.time()
        while len(self.sent_messages) >= self.rate_limit_per_min:
            elapsed = now - self.sent_messages[0]
            if elapsed < 60:
                time.sleep(1)
                now = time.time()
            else:
                self.sent_messages.popleft()
        self.sent_messages.append(now)

    def _send_raw(self, message):
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }

        for attempt in range(self.retries):
            try:
                if not TELEGRAM_URL:
                    logger.warning("TELEGRAM_URL not configured")
                    return False
                    
                response = requests.post(TELEGRAM_URL, data=payload, timeout=10)
                if response.status_code == 200:
                    return True
                
                logger.error(f"Telegram API Error: {response.text} (Attempt {attempt+1})")
                time.sleep(2 ** attempt) # Exponential backoff
            except Exception as e:
                logger.error(f"Network error on attempt {attempt+1}: {e}")
                time.sleep(2)
        return False

    def send_message(self, message):
        """Public method to queue a message."""
        msg_hash = hash(message)
        if msg_hash in self.seen_hashes:
            logger.info("Skipping duplicate message")
            return
        
        self.seen_hashes.append(msg_hash)
        self.msg_queue.put(message)

    def notify_trade(self, event_type, trade_data):
        """
        Preserves core signature.
        """
        message = format_trade_message(event_type, trade_data)
        self.send_message(message)
        return True # Accepted into queue
