from datetime import datetime
from typing import Dict, List, Optional

class LiveState:
    def __init__(self):
        self.capital: float = 100000.0
        self.daily_pnl: float = 0.0
        self.trades_today: int = 0
        self.active_positions: List[dict] = []
        self.regime: str = "Unknown"
        self.vix: float = 0.0
        self.status: str = "INACTIVE"
        self.last_heartbeat: Optional[datetime] = None
        self.recent_signals: List[dict] = [] # Last 50 signals
        self.mode: str = "PAPER"
        self.engines: List[str] = []
        self.risk_rules: dict = {}
        self.market_context: dict = {}

live_state = LiveState()
