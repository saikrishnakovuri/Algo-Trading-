import os
import time
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APS_AVAILABLE = True
except Exception:
    APS_AVAILABLE = False

from orchestrator import Orchestrator

class AlertSystem:
    def __init__(self, interval_minutes=15):
        self.interval = interval_minutes
        self.orch = Orchestrator()
        self.scheduler = None

    def send_alert(self, decision_text: str):
        # Placeholder: integrate with email/telegram/slack/webhook
        print("--- ALERT ---")
        print(decision_text)
        print("--- END ALERT ---")

    def start(self):
        if APS_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(self._job, 'interval', minutes=self.interval)
            self.scheduler.start()
            print(f"AlertSystem: scheduled every {self.interval} minutes")
        else:
            print("APScheduler not available; running single blocking loop (CTRL-C to stop)")
            try:
                while True:
                    self._job()
                    time.sleep(self.interval * 60)
            except KeyboardInterrupt:
                print("Stopped")

    def _job(self):
        decision = self.orch.run_cycle(dry_run=True)
        self.send_alert(decision)
