import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml

from modules.risk_exec.schemas import ApprovedSignal, TradeDecision, OpenPosition, MarketContext, RiskStatus
from modules.risk_exec.executor import TradeExecutor

class RiskTradeManagementEngine:
    """
    Facade for the entire Risk & Trade Management stack.
    """
    
    def __init__(self, config_path: str = "config/risk_execution.yaml", 
                 broker: Any = None,
                 trade_history_path: Path = Path("data/trade_history.parquet"), 
                 correlation_matrix_path: Path = Path("data/correlation_matrix.parquet")):
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        self.executor = TradeExecutor(self.config, broker, trade_history_path, correlation_matrix_path)
        
    def place_trade(
        self,
        signal: ApprovedSignal,
        current_equity: float,
        open_positions: List[OpenPosition],
        market_context: MarketContext
    ) -> TradeDecision:
        return self.executor.place_trade(signal, current_equity, open_positions, market_context)

    def manage_open_trades(
        self,
        open_positions: List[OpenPosition],
        current_bar_5m: pd.Series,
        current_bar_1m: pd.Series,
        market_context: MarketContext
    ) -> List[Any]:
        events = []
        for pos in open_positions:
            # 1. Check Trailing
            update = self.executor.trail_engine.check_trail(pos, market_context, current_bar_1m['high'], current_bar_1m['low'])
            if update:
                events.append(update)
                
            # 2. Check Exits (SL, Targets)
            # This is handled in backtest loop usually, but executor can provide logic
            pass
        return events

    def risk_status(self, current_equity: float) -> RiskStatus:
        return self.executor.breaker.get_status(current_equity)

    def record_trade_outcome(self, pnl: float):
        self.executor.breaker.record_trade(pnl)
