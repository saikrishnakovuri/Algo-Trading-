from apscheduler.schedulers.blocking import BlockingScheduler
import os
import time
import subprocess
import logging
from datetime import datetime
import sys
from notification.telegram_notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler("logs/overnight_scheduler.log"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Scheduler")
notifier = TelegramNotifier()

def run_task(script_name, description):
    logger.info(f"STARTING TASK: {description} ({script_name})")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        result = subprocess.run([sys.executable, script_name], capture_output=True, text=True, check=True, env=env)
        logger.info(f"COMPLETED TASK: {description}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"FAILED TASK: {description} | Error: {e.stderr}")
        notifier.send_message(f"❌ NIGHTLY ERROR: {description} failed!\n{e.stderr[:200]}")
        return False, e.stderr
    except Exception as e:
        logger.error(f"CRITICAL ERROR in {description}: {e}")
        return False, str(e)

def nightly_sequence():
    logger.info("=== STARTING NIGHTLY SEQUENCE ===")
    notifier.send_message("🌙 Nightly Maintenance Sequence Started.")
    
    # 1. Fetch Global Data
    # run_task("fetch_60_days.py", "Global Data Fetch")
    
    # 2. Enhanced WFO (20:45 IST)
    success, output = run_task("walk_forward_optimizer.py", "Walk-Forward Optimization")
    
    if success:
        notifier.send_message("✅ Nightly Optimization Complete. Parameters Updated & Backed up.")
    
    logger.info("=== NIGHTLY SEQUENCE FINISHED ===")

if __name__ == "__main__":
    if os.getenv("DRY_RUN_OPTIMIZATION", "0") == "1":
        logger.info("DRY RUN: Executing nightly sequence immediately...")
        nightly_sequence()
        sys.exit(0)

    logger.info("Overnight Scheduler Online (APScheduler). Waiting for 20:45 IST...")
    notifier.send_message("📅 Overnight Scheduler Online.")
    
    scheduler = BlockingScheduler()
    scheduler.add_job(nightly_sequence, 'cron', hour=20, minute=45)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
