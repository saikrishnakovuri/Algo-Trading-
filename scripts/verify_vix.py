import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from modules.broker_layer import BrokerClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VIXVerify")

def verify_vix():
    try:
        broker = BrokerClient()
        # Common index symbols
        test_symbols = [
            ("INDIA VIX", "NSE"),
            ("INDIAVIX", "NSE"),
            ("NIFTY VIX", "NSE")
        ]
        
        for sym, exch in test_symbols:
            try:
                # Look for LTP retrieval method in broker
                ltp = broker.get_ltp(sym, exchange=exch)
                print(f"[OK] {sym} ({exch}) = {ltp}")
                return
            except Exception:
                continue
        print("[FAIL] VIX not available via standard lookups")
    except Exception as e:
        print(f"[FAIL] Broker connection error: {e}")

if __name__ == "__main__":
    verify_vix()
