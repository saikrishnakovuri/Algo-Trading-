import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s | CRYPTO | %(message)s')
logger = logging.getLogger("crypto_trader")

def crypto_trader():
    logger.info("CRYPTO TRADER STUB ONLINE (24/7 Mode)")
    while True:
        logger.info(f"Scanning Binance for signals... {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(60)

if __name__ == "__main__":
    try:
        crypto_trader()
    except KeyboardInterrupt:
        logger.info("Crypto trader stopped.")
