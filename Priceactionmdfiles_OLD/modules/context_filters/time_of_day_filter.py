import pytz
from datetime import datetime, time, timedelta
try:
    from typing import Dict, Any, Optional, Union
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, Optional, Union
    Literal = Any
from modules.context_filters.calendar import TradingCalendar
from modules.context_filters.schemas import TimeOfDayVerdict

class TimeOfDayFilter:
    """
    Dual-window time-of-day filter with profile-specific rules.
    """
    
    def __init__(self, config: Dict[str, Any], calendar: TradingCalendar):
        self.config = config['time_of_day']
        self.cal = calendar
        self.tz = pytz.timezone(self.config['timezone'])
        
    def evaluate(self, now_ist: datetime, signal_type: str, 
                 ohlcv_1m_len: int, regime: str) -> TimeOfDayVerdict:
        """
        now_ist: Current time in IST.
        """
        curr_time = now_ist.time()
        curr_date = now_ist.date()
        
        # 1. SPECIAL DAYS OVERRIDES
        is_weekly = self.cal.is_weekly_expiry(curr_date)
        is_monthly = self.cal.is_monthly_expiry(curr_date)
        
        # Determine effective end time
        standard_end = time.fromisoformat(self.config['windows']['trend_development']['end'])
        effective_end = standard_end
        
        threshold_bump = 0.0
        if is_monthly:
            effective_end = time.fromisoformat(self.config['special_days']['monthly_expiry']['end_override'])
            threshold_bump = self.config['special_days']['monthly_expiry']['threshold_bump']
        elif is_weekly:
            effective_end = time.fromisoformat(self.config['special_days']['weekly_expiry']['end_override'])
            threshold_bump = self.config['special_days']['weekly_expiry']['threshold_bump']

        # Check for event blackouts
        events = self.cal.scheduled_events(curr_date)
        for e in events:
            e_time = datetime.strptime(e.time, "%H:%M").time()
            e_dt = datetime.combine(curr_date, e_time)
            blackout_start = (e_dt - timedelta(minutes=e.blackout_pre_min)).time()
            blackout_end = (e_dt + timedelta(minutes=e.blackout_post_min)).time()
            if blackout_start <= curr_time <= blackout_end:
                return TimeOfDayVerdict(verdict="VETO", active_window="EVENT_BLACKOUT", sub_window=None, 
                                        setup_weight_multiplier=0.0, score_threshold_delta=0.0, 
                                        max_concurrent_override=0, reasoning=f"Event Blackout: {e.name}")

        # 2. WINDOW CLASSIFICATION
        
        # Window A: OPENING_BURST (09:15 - 09:45)
        w_a = self.config['windows']['opening_burst']
        w_a_start = time.fromisoformat(w_a['start'])
        w_a_end = time.fromisoformat(w_a['end'])
        
        if w_a_start <= curr_time < w_a_end:
            # Data sufficiency check
            if ohlcv_1m_len < w_a['min_1m_bars_before_entry']:
                return TimeOfDayVerdict(verdict="VETO", active_window="OPENING_BURST", sub_window=None,
                                        setup_weight_multiplier=0.0, score_threshold_delta=0.0,
                                        max_concurrent_override=None, reasoning="Insufficient bars since open")
            
            # Setup bias
            mult = 1.0
            if signal_type == "BREAKOUT":
                mult = w_a['breakout_weight']
            
            return TimeOfDayVerdict(
                verdict="ALLOW",
                active_window="OPENING_BURST",
                sub_window=None,
                setup_weight_multiplier=mult,
                score_threshold_delta=w_a['threshold_delta'] + threshold_bump,
                max_concurrent_override=None,
                reasoning="High volatility opening window"
            )

        # Window B: TREND_DEVELOPMENT (09:45 - 13:30/12:30)
        w_b = self.config['windows']['trend_development']
        w_b_start = time.fromisoformat(w_b['start'])
        
        if w_b_start <= curr_time < effective_end:
            # Sub-window logic
            sub_name = "pre_lunch"
            delta = w_b['threshold_delta']
            
            for sn, cfg in w_b['sub_windows'].items():
                s = time.fromisoformat(cfg['start'])
                e = time.fromisoformat(cfg['end'])
                if s <= curr_time < e:
                    sub_name = sn
                    delta = cfg['threshold_delta']
                    break
            
            # Setup bias
            mult = 1.0
            if signal_type == "TRAP_FADE":
                mult = w_b['trap_fade_weight']
            
            return TimeOfDayVerdict(
                verdict="ALLOW",
                active_window="TREND_DEVELOPMENT",
                sub_window=sub_name,
                setup_weight_multiplier=mult,
                score_threshold_delta=delta + threshold_bump,
                max_concurrent_override=None, # Caller handles regime × 0.75
                reasoning=f"Trend development ({sub_name})"
            )

        # Window C: NO_NEW_ENTRIES
        return TimeOfDayVerdict(
            verdict="VETO",
            active_window="NO_NEW_ENTRIES",
            sub_window=None,
            setup_weight_multiplier=0.0,
            score_threshold_delta=0.0,
            max_concurrent_override=0,
            reasoning="Outside trading hours"
        )
