from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional
from modules.risk_exec.schemas import TimeStopPolicy, OpenPosition, MarketContext

class ContextAwareTimeStop:
    """
    Computes adaptive time stops based on setup type, regime, and momentum.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config['time_stop']
        
    def get_policy(self, position: OpenPosition, context: MarketContext) -> TimeStopPolicy:
        setup = position.metadata.get('setup_type', 'OTHER')
        base_min = self.config['base_minutes'].get(setup, 30)
        
        regime_mult = self.config['regime_multipliers'].get(context.regime, 1.0)
        
        total_min = base_min * regime_mult
        
        initial_deadline = position.entry_ts + timedelta(minutes=total_min)
        mid_check_deadline = position.entry_ts + timedelta(minutes=total_min / 2)
        
        # Hard Cutoffs
        hard_cut = self._get_hard_cutoff(position, context)
        
        return TimeStopPolicy(
            initial_deadline=initial_deadline,
            mid_check_deadline=mid_check_deadline,
            hard_cutoff=hard_cut,
            reasoning=f"Base {base_min}m x Regime {regime_mult} = {total_min}m total PATIENCE."
        )

    def _get_hard_cutoff(self, position: OpenPosition, context: MarketContext) -> datetime:
        # Default session end
        now = position.entry_ts
        expiry_time = time.fromisoformat(self.config['hard_cutoffs']['expiry_close'])
        
        # Window-specific
        if context.active_window == "OPENING_BURST":
            cutoff_t = time.fromisoformat(self.config['hard_cutoffs']['window_a_close'])
        else:
            cutoff_t = time.fromisoformat(self.config['hard_cutoffs']['window_b_close'])
            
        return datetime.combine(now.date(), cutoff_t)

    def check_progress(self, position: OpenPosition, policy: TimeStopPolicy, 
                       now: datetime, current_r: float) -> Optional[str]:
        """
        Returns 'TIGHTEN' or 'FORCE_CLOSE' if policy violated.
        """
        if now >= policy.hard_cutoff:
            return "FORCE_CLOSE_HARD_CUTOFF"
            
        # GRADUATED TIME MANAGEMENT
        elapsed_min = (now - position.entry_ts).total_seconds() / 60
        
        # 20 min: If losing, cut immediately
        if 20 <= elapsed_min < 25 and current_r < 0:
            return "FORCE_CLOSE_20M_LOSING"

        # 45 min: If below 0.5R, signal to move SL to entry (breakeven protection)
        if 45 <= elapsed_min < 50:
            if 0 < current_r < 0.5:
                return "TIGHTEN_SL_BREAKEVEN"
            elif current_r <= 0:
                return "FORCE_CLOSE_45M_STALLED"

        # 90 min: Hard close anything still open below 1.0R
        if 90 <= elapsed_min < 95:
            if current_r < 1.0:
                return "FORCE_CLOSE_90M_FINAL"

        # 150 min: Absolute hard close
        if elapsed_min >= 150:
            return "FORCE_CLOSE_EOD_SAFETY"
                
        return None
