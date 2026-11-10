import time
from notification.telegram_notifier import TelegramNotifier

def run_test():
    print("Testing Telegram Notifier...")
    notifier = TelegramNotifier()
    
    # 1. Send Simple System Message
    notifier.send_message("🛠️ *BOT TEST*: Connection Verification for Tomorrow's Session.")
    
    # 2. Send Mock Trade Entry
    print("Sending Mock Trade Entry...")
    notifier.notify_trade("ENTRY", {
        "symbol": "RELIANCE",
        "direction": "CE",
        "price": 2540.50,
        "size": 42,
        "score": 8.75,
        "regime": "TRENDING_LOW_VOL",
        "rr": "1:2"
    })
    
    print("Test complete. Check your Telegram!")
    # Small sleep to let the background worker process
    time.sleep(5)

if __name__ == "__main__":
    run_test()
