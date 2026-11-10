# modules/dashboard_bridge.py
import threading, requests, logging
from datetime import datetime
from modules.v3_utils import DASHBOARD_URL

logger = logging.getLogger(__name__)

class DashboardBridge:
    def __init__(self):
        self.enabled = True
        self.base_url = DASHBOARD_URL

    def _send(self, event_type: str, payload: dict):
        try:
            payload["timestamp"] = datetime.now().isoformat()
            requests.post(
                f"{self.base_url}/api/bot/{event_type}",
                json=payload, timeout=2
            )
        except Exception as e:
            logger.warning(f"[Bridge] Failed to push {event_type}: {e}")

    def push(self, event_type: str, payload: dict):
        if not self.enabled:
            return
        t = threading.Thread(target=self._send, args=(event_type, payload), daemon=True)
        t.start()

    def boot(self, config: dict):
        self.push("BOOT", {"config": config})

    def signal(self, symbol, direction, strategy, confidence, context_tags):
        self.push("SIGNAL", {"symbol": symbol, "direction": direction,
                             "strategy": strategy, "confidence": confidence,
                             "context_tags": context_tags})

    def trade_open(self, trade_id, symbol, direction, entry_price, lots,
                   sl, tp, strategy, context_tags):
        self.push("TRADE_OPEN", {"trade_id": trade_id, "symbol": symbol,
                                  "direction": direction, "entry_price": entry_price,
                                  "lots": lots, "sl": sl, "tp": tp,
                                  "strategy": strategy, "context_tags": context_tags})

    def trade_close(self, trade_id, exit_price, exit_reason, pnl, r_multiple):
        self.push("TRADE_CLOSE", {"trade_id": trade_id, "exit_price": exit_price,
                                   "exit_reason": exit_reason, "pnl": pnl,
                                   "r_multiple": r_multiple})

    def trade_update(self, trade_id, current_price, unrealised_pnl):
        self.push("TRADE_UPDATE", {"trade_id": trade_id,
                                    "current_price": current_price,
                                    "unrealised_pnl": unrealised_pnl})

    def heartbeat(self, regime, vix, capital, trades_today,
                  consecutive_losses, bot_mode, is_paused, active_positions=[]):
        self.push("HEARTBEAT", {"regime": regime, "vix": vix,
                                 "capital": capital, "trades_today": trades_today,
                                 "consecutive_losses": consecutive_losses,
                                 "bot_mode": bot_mode, "is_paused": is_paused,
                                 "active_positions": active_positions})

    def daily_summary(self, date, total_trades, wins, losses,
                      net_pnl, closing_capital):
        self.push("DAILY_SUMMARY", {"date": date, "total_trades": total_trades,
                                     "wins": wins, "losses": losses,
                                     "net_pnl": net_pnl,
                                     "closing_capital": closing_capital})

bridge = DashboardBridge()  # singleton
