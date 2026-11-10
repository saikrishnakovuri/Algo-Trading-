import pandas as pd
from datetime import datetime
from pathlib import Path
try:
    from typing import Dict, Any, List, Optional, Union
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, List, Optional, Union
    Literal = Any
from modules.context_filters.schemas import AllowDecision, ChopVerdict, TimeOfDayVerdict, GapVerdict
from modules.context_filters.chop_filter import ChopFilter
from modules.context_filters.time_of_day_filter import TimeOfDayFilter
from modules.context_filters.gap_filter import GapAlignmentFilter
from modules.context_filters.calendar import TradingCalendar

class ContextFilterStack:
    """
    Orchestrates the context filters (Time, Gap, Chop) as a hard veto gate.
    """
    
    def __init__(self, config: Dict[str, Any], calendar: TradingCalendar, 
                 gap_stats_path: Path):
        self.config = config
        self.calendar = calendar
        self.time_filter = TimeOfDayFilter(config, calendar)
        self.gap_filter = GapAlignmentFilter(config, gap_stats_path)
        self.chop_filter = ChopFilter(config)
        
    def evaluate(
        self,
        symbol: str,
        signal_direction: str,
        signal_type: str,
        now_ist: datetime,
        ohlcv_5m: pd.DataFrame,
        ohlcv_1m: pd.DataFrame,
        prior_close: float,
        today_open: float,
        atr_14_5m: float,
        atr_14_daily: float,
        regime: str,
        sweep_at_gap_level: bool = False,
        retracement_pct: float = 0.0,
        volume_first_10min: Optional[float] = None,
        volume_first_10min_avg: Optional[float] = None,
        nifty_gap_pct: Optional[float] = None,
        stock_event_tagged: bool = False,
        backtest_mode: bool = False
    ) -> AllowDecision:
        
        # 0. Stock Event Check (Converted guardrail)
        try:
            event_today = self.calendar.stock_event_today(symbol, backtest_mode=backtest_mode)
            if event_today:
                 return self._build_decision(False, None, None, None, symbol, "Stock Event Day")
        except RuntimeError as e:
            if not backtest_mode: raise e
        
        # 1. TimeOfDayFilter (Fastest)
        tod_verdict = self.time_filter.evaluate(now_ist, signal_type, len(ohlcv_1m), regime)
        if tod_verdict.verdict == "VETO":
            return self._build_decision(False, tod_verdict, None, None, symbol)
            
        # 2. GapAlignmentFilter
        gap_pct = (today_open - prior_close) / prior_close * 100 if prior_close > 0 else 0
        gap_atr = (today_open - prior_close) / atr_14_daily if atr_14_daily > 0 else 0
        gap_verdict = self.gap_filter.evaluate(gap_pct, gap_atr, signal_direction, now_ist, retracement_pct, sweep_at_gap_level)
        
        if gap_verdict.verdict == "VETO":
            return self._build_decision(False, tod_verdict, gap_verdict, None, symbol)
            
        # 3. ChopFilter
        chop_verdict = self.chop_filter.evaluate(ohlcv_5m, atr_14_5m, regime)
        if chop_verdict.verdict == "VETO":
            return self._build_decision(False, tod_verdict, gap_verdict, chop_verdict, symbol)

        # ALL PASSED (or WARN)
        return self._build_decision(True, tod_verdict, gap_verdict, chop_verdict, symbol)

    def _build_decision(self, allow: bool, tod: TimeOfDayVerdict, 
                        gap: Optional[GapVerdict], chop: Optional[ChopVerdict], 
                        symbol: str) -> AllowDecision:
        
        veto_reasons = []
        warnings = []
        
        if tod.verdict == "VETO": veto_reasons.append(f"Time: {tod.reasoning}")
        if gap and gap.verdict == "VETO": veto_reasons.append(f"Gap: {gap.reasoning}")
        if chop and chop.verdict == "VETO": veto_reasons.append(f"Chop: {chop.reasoning}")
        
        if chop and chop.verdict == "WARN": warnings.append(f"Chop Warning: {chop.reasoning}")
        
        mult = tod.setup_weight_multiplier
        if gap: mult *= gap.weight_multiplier
        
        return AllowDecision(
            allow_trade=allow,
            combined_weight_multiplier=round(mult, 2),
            combined_threshold_delta=tod.score_threshold_delta,
            veto_reasons=veto_reasons,
            warnings=warnings,
            chop=chop or ChopVerdict("ALLOW", 0.0, {}, 0.6, "N/A"),
            time_of_day=tod,
            gap=gap or GapVerdict("ALLOW", "micro", "NONE", 0.0, 0.0, 0.5, "NEUTRAL", 1.0, False, "N/A"),
            evaluated_at=datetime.now(),
            symbol=symbol
        )
