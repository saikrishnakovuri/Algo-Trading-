import asyncio
import threading
from typing import Dict, List, Optional

class PortfolioManager:
    """
    Manages total portfolio equity, compounding, and global risk limits.
    """
    def __init__(self, initial_capital=500000.0):
        self.starting_equity = float(initial_capital)
        self.total_equity = initial_capital
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.daily_pnl = 0.0
        self.risk_budget_pct = 0.01
        self.daily_circuit_breaker_pct = 0.02
        self.max_daily_risk = self.total_equity * self.risk_budget_pct
        self.active_risk = 0.0
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason: Optional[str] = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def update_equity(self, pnl: float):
        with self._lock:
            self.realized_pnl += pnl
            self.total_equity += pnl
            self.daily_pnl += pnl
            # Recalculate daily risk limit based on new total equity
            self.max_daily_risk = self.total_equity * self.risk_budget_pct
            self._check_circuit_breaker_locked()

    def daily_reset(self):
        with self._lock:
            self.starting_equity = self.total_equity
            self.realized_pnl = 0.0
            self.unrealized_pnl = 0.0
            self.daily_pnl = 0.0
            self.active_risk = 0.0
            self.circuit_breaker_tripped = False
            self.circuit_breaker_reason = None

    def can_enter_trade(self, risk_amount: float) -> bool:
        with self._lock:
            if self.circuit_breaker_tripped:
                return False
            if (self.active_risk + risk_amount) <= self.max_daily_risk:
                self.active_risk += risk_amount
                return True
            return False

    def remove_risk(self, risk_amount: float):
        with self._lock:
            self.active_risk = max(0.0, self.active_risk - risk_amount)

    def update_unrealized_pnl(self, positions: List[Dict], prices: Dict[str, float]) -> Dict:
        """Refresh mark-to-market PnL and trip the 2% daily breaker if needed."""
        with self._lock:
            unrealized = 0.0
            for position in positions:
                symbol = position.get("symbol")
                if symbol not in prices:
                    continue
                qty = int(position.get("qty", 0))
                side = str(position.get("side", "LONG")).upper()
                entry = float(position.get("entry_price", 0.0))
                ltp = float(prices[symbol])
                direction = 1 if side in {"LONG", "BUY", "CE"} else -1
                unrealized += (ltp - entry) * qty * direction

            self.unrealized_pnl = unrealized
            self.daily_pnl = self.realized_pnl + self.unrealized_pnl
            self._check_circuit_breaker_locked()
            return self._snapshot_locked()

    async def async_update_unrealized_pnl(self, positions: List[Dict], prices: Dict[str, float]) -> Dict:
        async with self._async_lock:
            # These are simple mathematical operations, so run_in_executor adds unnecessary overhead.
            # Running directly inside the async lock is faster and completely safe.
            return self.update_unrealized_pnl(positions, prices)

    async def async_can_enter_trade(self, risk_amount: float) -> bool:
        async with self._async_lock:
            return self.can_enter_trade(risk_amount)

    async def async_update_equity(self, pnl: float):
        async with self._async_lock:
            return self.update_equity(pnl)

    def is_circuit_breaker_tripped(self) -> bool:
        with self._lock:
            return self.circuit_breaker_tripped

    def snapshot(self) -> Dict:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> Dict:
        return {
            "starting_equity": round(self.starting_equity, 2),
            "total_equity": round(self.total_equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "active_risk": round(self.active_risk, 2),
            "max_trade_risk": round(self.max_daily_risk, 2),
            "daily_circuit_breaker": round(-(self.starting_equity * self.daily_circuit_breaker_pct), 2),
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "circuit_breaker_reason": self.circuit_breaker_reason,
        }

    def _check_circuit_breaker_locked(self):
        breaker = -(self.starting_equity * self.daily_circuit_breaker_pct)
        if self.daily_pnl <= breaker:
            self.circuit_breaker_tripped = True
            self.circuit_breaker_reason = "DAILY_CIRCUIT_BREAKER_2_PERCENT"
