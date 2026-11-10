"""
Tracks per-strategy performance and adapts confidence 
thresholds over time.
Runs as background process — never blocks main loop.
"""

import threading
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class StrategyLearner:

    LEARNING_WINDOW_DAYS = 30  # evaluate last 30 days
    MIN_TRADES_FOR_SIGNAL = 20 # need 20+ trades to adjust

    def __init__(self, db):
        self.db = db
        self._adjustments = {}  # strategy → confidence delta

    def get_adjusted_threshold(self, strategy: str,
                                base_threshold: float) -> float:
        """Returns base threshold adjusted by recent performance."""
        delta = self._adjustments.get(strategy, 0)
        return max(40, min(90, base_threshold + delta))

    def run_background_analysis(self):
        """Call once per day (after market close)."""
        t = threading.Thread(target=self._analyze, daemon=True)
        t.start()

    def _analyze(self):
        """
        For each strategy:
        1. Pull last 30 days trades from MongoDB
        2. Compute win rate and profit factor
        3. Adjust confidence threshold up/down
        4. Save adjustments to MongoDB
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(
                days=self.LEARNING_WINDOW_DAYS
            )
            # Use 'trades' collection as established in server.py
            strategies = list(self.db["trades"].distinct("strategy_name"))
            if not strategies:
                strategies = list(self.db["trades"].distinct("strategy"))

            for strategy in strategies:
                query = {
                    "$or": [{"strategy_name": strategy}, {"strategy": strategy}],
                    "event_type": {"$in": ["exit", "sl", "tp", "TRADE_CLOSE"]},
                    "timestamp": {"$gte": cutoff.isoformat()}
                }
                trades = list(self.db["trades"].find(query))

                if len(trades) < self.MIN_TRADES_FOR_SIGNAL:
                    continue

                pnls    = [float(t.get("pnl_abs", 0)) for t in trades]
                wins    = [p for p in pnls if p > 0]
                win_rate = len(wins) / len(pnls)
                losses  = [p for p in pnls if p <= 0]
                
                abs_win_sum = abs(sum(wins))
                abs_loss_sum = abs(sum(losses))
                pf = (abs_win_sum / abs_loss_sum
                      if abs_loss_sum != 0 else 1.0)

                # ── Adjustment Logic ─────────────────
                # Great performance → lower threshold (more trades)
                # Poor performance → raise threshold (fewer trades)
                if win_rate > 0.55 and pf > 1.5:
                    delta = -5   # lower threshold by 5 pts (more aggressive)
                elif win_rate > 0.48 and pf > 1.2:
                    delta = 0    # no change
                elif win_rate < 0.40 or pf < 0.9:
                    delta = +10  # raise threshold by 10 pts (more conservative)
                else:
                    delta = +5   # slight caution

                self._adjustments[strategy] = delta

                # Save to MongoDB
                self.db["strategy_performance"].update_one(
                    {"strategy": strategy},
                    {"$set": {
                        "strategy":    strategy,
                        "trades":      len(trades),
                        "win_rate":    round(win_rate, 3),
                        "profit_factor": round(pf, 2),
                        "net_pnl":     round(sum(pnls), 2),
                        "threshold_delta": delta,
                        "updated_at":  datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
            logger.info(f"[Learner] Analysis completed for {len(strategies)} strategies.")

        except Exception as e:
            logger.warning(f"[Learner] Analysis failed: {e}")
