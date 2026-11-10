import subprocess
import time
import sys
import os
import signal
import redis
import argparse
import logging
from datetime import datetime
from notification.telegram_notifier import TelegramNotifier

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | LAUNCHER | %(message)s',
    handlers=[logging.FileHandler("logs/launcher.log"), logging.StreamHandler()]
)
logger = logging.getLogger("launcher")

class ProductionLauncher:
    def __init__(self, mode="PAPER", tier="123", symbols=None):
        self.mode = mode
        self.tier_str = tier
        self.symbols = symbols
        self.processes = {}
        self.notifier = TelegramNotifier()
        self.is_running = True

    def check_redis(self):
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            info = r.info('memory')
            logger.info(f"Redis check — OK (used_memory: {info['used_memory_human']})")
            return True
        except Exception as e:
            logger.warning(f"Redis not running, using module-level stubs: {e}")
            os.environ["SKIP_REDIS_CHECK"] = "1"
            return True

    def run_backfill(self):
        if os.getenv("SKIP_REDIS_CHECK") == "1":
            logger.info("Skipping backfill (Redis down).")
            return
        logger.info("Running market-open backfill...")
        try:
            subprocess.run([sys.executable, "scripts/backfill_at_open.py"], check=True)
            logger.info("Backfill complete.")
        except Exception as e:
            logger.error(f"Backfill failed: {e}")

    def start_process(self, name, command):
        logger.info(f"Starting {name}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        if os.getenv("SKIP_REDIS_CHECK") == "1":
            env["SKIP_REDIS_CHECK"] = "1"
            
        proc = subprocess.Popen([sys.executable] + command, env=env)
        self.processes[name] = {"proc": proc, "cmd": command, "restarts": 0}
        return proc

    def monitor(self):
        logger.info("Watchdog active. Monitoring systems...")
        while self.is_running:
            now_dt = datetime.now()
            now = now_dt.time()
            is_weekend = now_dt.weekday() >= 5
            
            # Indian Market Hours (9:15 AM to 3:30 PM)
            nse_start = datetime.strptime("09:15:00", "%H:%M:%S").time()
            nse_end = datetime.strptime("15:30:00", "%H:%M:%S").time()
            is_nse_hours = nse_start <= now <= nse_end and not is_weekend

            for name, data in list(self.processes.items()):
                # SPECIAL CASE: Crypto Trader (Only run outside NSE hours)
                if name == "CryptoTrader":
                    if is_nse_hours:
                        if data['proc'] and hasattr(data['proc'], 'poll') and data['proc'].poll() is None:
                            logger.info("NSE HOURS: Stopping Crypto Trader.")
                            data['proc'].terminate()
                        continue 
                    else:
                        # Outside NSE hours - should be running
                        if not data['proc'] or (hasattr(data['proc'], 'poll') and data['proc'].poll() is not None):
                            logger.info("OFF-HOURS: Starting/Restarting Crypto Trader.")
                            self.start_process("CryptoTrader", ["live_trader_crypto.py"])
                    continue

                # SPECIAL CASE: TraderV3 (Only run during NSE hours)
                if name == "TraderV3":
                    if not is_nse_hours:
                        if data['proc'] and hasattr(data['proc'], 'poll') and data['proc'].poll() is None:
                            logger.info("OFF-HOURS: Stopping TraderV3.")
                            data['proc'].terminate()
                        continue
                    # Else fall through to normal watchdog logic if it's NSE hours

                proc = data['proc']
                if not proc or proc.poll() is not None:
                    exit_code = proc.returncode if proc else "N/A"
                    logger.warning(f"WATCHDOG: Process {name} died/not-started (exit code {exit_code})")
                    
                    if data['restarts'] < 10: # Increased limit
                        data['restarts'] += 1
                        logger.info(f"Restarting {name} ({data['restarts']}/10)...")
                        self.start_process(name, data['cmd'])
                        # Update the entry in self.processes with the new proc
                    else:
                        logger.error(f"WATCHDOG: Process {name} failed too many times.")
                        self.notifier.send_message(f"🚨 CRITICAL: Process {name} failed 10 times.")
            time.sleep(10)

    def stop(self):
        self.is_running = False
        logger.info("Stopping all systems gracefully...")
        for name in list(self.processes.keys()):
            proc = self.processes[name]['proc']
            if proc and hasattr(proc, 'poll') and proc.poll() is None:
                logger.info(f"Stopping {name}...")
                proc.terminate()
        time.sleep(5)
        for name, data in self.processes.items():
            proc = data['proc']
            if proc and hasattr(proc, 'poll') and proc.poll() is None:
                proc.kill()
        logger.info("Launcher exit.")

def main():
    parser = argparse.ArgumentParser(description="Production Scaled Launcher V2")
    parser.add_argument("--mode", default="PAPER", choices=["PAPER", "LIVE"])
    parser.add_argument("--tier", default="123")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--crypto", action="store_true", help="Start crypto trader immediately")
    args = parser.parse_args()

    launcher = ProductionLauncher(mode=args.mode, tier=args.tier, symbols=args.symbols)
    launcher.check_redis()
    launcher.run_backfill()
    
    # 1. Start Core Bot
    launcher.start_process("TraderV3", ["live_trader_v3.py"])
    
    # 2. Start Scheduler
    launcher.start_process("Scheduler", ["overnight_scheduler.py"])
    
    # 3. Start Crypto Trader
    if args.crypto:
        launcher.start_process("CryptoTrader", ["live_trader_crypto.py"])
    else:
        now = datetime.now().time()
        nse_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        nse_end = datetime.strptime("15:30:00", "%H:%M:%S").time()
        
        if not (nse_start <= now <= nse_end):
            launcher.start_process("CryptoTrader", ["live_trader_crypto.py"])
        else:
            logger.info("NSE HOURS: Skipping Crypto Trader startup.")
            launcher.processes["CryptoTrader"] = {"proc": None, "cmd": ["live_trader_crypto.py"], "restarts": 0}

    if os.getenv("SKIP_REDIS_CHECK") != "1":
        launcher.start_process("Feed", ["modules/data/websocket_feed.py"])
        launcher.start_process("Builder", ["modules/data/candle_builder.py"])

    def signal_handler(sig, frame):
        launcher.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    launcher.monitor()

if __name__ == "__main__":
    main()
