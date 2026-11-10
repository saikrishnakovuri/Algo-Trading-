import logging
from modules.v3_utils import NOTIFIER_TOKEN, TELEGRAM_CHAT_ID

# Basic logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramTest")

def test_telegram():
    from modules.notifier import TelegramNotifier
    try:
        notifier = TelegramNotifier(token=NOTIFIER_TOKEN, chat_id=TELEGRAM_CHAT_ID)
        notifier.send_message("Paper trade bot ready. System check OK.")
        print("[OK] Test message sent successfully.")
    except Exception as e:
        print(f"[FAIL] Telegram send failed: {e}")

if __name__ == "__main__":
    test_telegram()
