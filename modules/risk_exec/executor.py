import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from modules.risk_exec.schemas import (
    ApprovedSignal, TradeDecision, OpenPosition, MarketContext, 
    HeatCheckResult, RiskStatus, TrailUpdate, ExitEvent
)
from modules.risk_exec.sizer import AdaptivePositionSizer
from modules.risk_exec.stop_loss import VolatilityAdaptiveStopLoss
from modules.risk_exec.exits import MultiTargetExitPlanner
from modules.risk_exec.trailing import AdaptiveTrailingEngine
from modules.risk_exec.time_stop import ContextAwareTimeStop
from modules.risk_exec.heat_manager import CorrelationAwareHeatManager
from modules.risk_exec.breaker import DrawdownCircuitBreaker
from modules.risk_exec.execution_quality import ExecutionQualityTracker

class TradeExecutor:
    """
    Orchestrates the full lifecycle of a trade using the risk-execution stack.
    """
    
    def __init__(self, config: Dict[str, Any], broker: Any, 
                 trade_history_path: Any, correlation_matrix_path: Any):
        self.config = config
        self.broker = broker
        
        self.sizer = AdaptivePositionSizer(config, trade_history_path)
        self.sl_calc = VolatilityAdaptiveStopLoss(config)
        self.exit_planner = MultiTargetExitPlanner(config)
        self.trail_engine = AdaptiveTrailingEngine(config)
        self.time_stop_calc = ContextAwareTimeStop(config)
        self.heat_manager = CorrelationAwareHeatManager(config, correlation_matrix_path)
        self.breaker = DrawdownCircuitBreaker(config)
        self.exec_quality = ExecutionQualityTracker(config)

    def place_trade(self, signal: ApprovedSignal, current_equity: float, 
                    open_positions: List[OpenPosition], context: MarketContext) -> TradeDecision:
        
        # 1. Risk Status check
        day_start_equity = current_equity # Simplification
        risk_status = self.breaker.get_status(day_start_equity)
        if risk_status.tier == 4:
            return self._veto("CIRCUIT_BREAKER_HALT", risk_status)
            
        # 2. Stop Loss Calculation
        # need zone bounds from signal metadata or context
        z_low = signal.metadata.get('zone_low', signal.entry_price * 0.99)
        z_high = signal.metadata.get('zone_high', signal.entry_price * 1.01)
        sl_dec = self.sl_calc.calculate(signal, context, z_low, z_high)
        
        # REMOVED: Hard Veto on SL_TOO_WIDE. The position sizer will handle the wider SL
        # by reducing the quantity (shares).
        # if "SL_TOO_WIDE" in sl_dec.guardrails_hit:
        #     return self._veto("STOP_LOSS_TOO_WIDE", risk_status)

        # 3. Sizing
        sizing = self.sizer.calculate(signal, current_equity, sl_dec.sl_price, context.stock_adv)
        if sizing.shares == 0:
            return self._veto(sizing.reasoning, risk_status)
            
        # Apply breaker multiplier
        sizing.shares = int(sizing.shares * risk_status.size_multiplier)
        if sizing.shares == 0:
            return self._veto("BREAKER_SIZE_REDUCTION_TO_ZERO", risk_status)

        # 4. Heat check
        heat_check = self.heat_manager.check_heat(signal, current_equity, open_positions, sizing.risk_amount)
        if not heat_check.allow:
            return self._veto(heat_check.veto_reason, risk_status, heat_check)

        # 5. Exit Plan
        exits = self.exit_planner.calculate(signal, context, sl_dec.per_share_risk)
        
        # 6. Time Stop policy
        # Need dummy position to get timestamps
        dummy_pos = OpenPosition("dummy", signal.symbol, signal.direction, signal.entry_price, signal.signal_ts, sizing.shares, sizing.shares, sl_dec.sl_price, exits.targets, 1, 0.0, {})
        time_stop = self.time_stop_calc.get_policy(dummy_pos, context)
        
        # 7. EXECUTE (Simulated in backtest)
        # Model slippage
        exec_info = self.exec_quality.model_execution(signal, sizing.shares)
        
        # All good, return execution decision
        return TradeDecision(
            action="EXECUTED",
            order_ref=str(uuid.uuid4()),
            sizing=sizing,
            sl=sl_dec,
            exits=exits,
            time_stop=time_stop,
            heat_check=heat_check,
            risk_status=risk_status,
            veto_reason=None,
            reasoning="All risk checks passed. Context-aware parameters applied."
        )

    def _veto(self, reason: str, risk_status: RiskStatus, 
              heat: HeatCheckResult = None) -> TradeDecision:
        if heat is None:
            heat = HeatCheckResult(False, 0, 0, 0, 0, reason)
        return TradeDecision("VETOED", None, None, None, None, None, heat, risk_status, reason, f"Vetoed: {reason}")
