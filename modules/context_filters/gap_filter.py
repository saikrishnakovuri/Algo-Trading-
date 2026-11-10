import joblib
import pandas as pd
from pathlib import Path
try:
    from typing import Dict, Any, Optional, Union
    from typing_extensions import Literal
except ImportError:
    from typing import Dict, Any, Optional, Union
    Literal = Any
from modules.context_filters.schemas import GapVerdict

class GapAlignmentFilter:
    """
    Statistical gap alignment filter.
    Categorizes gaps and checks historical fill probabilities.
    """
    
    def __init__(self, config: Dict[str, Any], stats_path: Path):
        self.config = config['gap']
        self.stats_path = stats_path
        self.stats_df = None
        if stats_path.exists():
            self.stats_df = joblib.load(stats_path)
        
    def evaluate(self, gap_pct: float, gap_atr: float, signal_direction: str, 
                 curr_time_ist: Any, retracement_pct: float = 0.0,
                 sweep_at_gap: bool = False) -> GapVerdict:
        
        abs_gap_pct = abs(gap_pct)
        gap_dir = "BULL" if gap_pct >= 0 else "BEAR"
        
        # 1. Categorize (FIX: Correct sequential check)
        cat = "extreme"
        # Ordered by size to catch the smallest match
        for c in ["micro", "small", "medium", "large"]:
            cfg = self.config['categories'][c]
            if abs_gap_pct <= cfg['pct'] and abs(gap_atr) <= cfg['atr']:
                cat = c
                break
                
        # 2. Historical Prob (Placeholder if stats missing)
        fill_prob = 0.5
        if self.stats_df is not None:
            mask = (self.stats_df['category'] == cat) & (self.stats_df['direction'] == gap_dir)
            if any(mask):
                fill_prob = float(self.stats_df[mask]['filled'].mean())

        # 3. Decision Matrix
        alignment = "NEUTRAL"
        if (signal_direction == "LONG" and gap_dir == "BULL") or \
           (signal_direction == "SHORT" and gap_dir == "BEAR"):
            alignment = "ALIGNED"
        elif (signal_direction == "LONG" and gap_dir == "BEAR") or \
             (signal_direction == "SHORT" and gap_dir == "BULL"):
            alignment = "CONTRA"

        verdict = "ALLOW"
        mult = 1.0
        reasoning = f"{cat.upper()} {gap_dir} gap ({gap_pct:.2f}%)"
        
        if cat in ["micro", "small"]:
            verdict = "ALLOW"
            if alignment == "CONTRA":
                mult = self.config['weight_multipliers']['contra'].get(cat, 1.0)
        elif cat == "medium":
            if alignment == "CONTRA":
                if retracement_pct < self.config['retracement_thresholds']['medium_contra_min']:
                    verdict = "VETO"
                    reasoning += " | Contra-gap needs 50% retrace"
        elif cat == "large":
            if alignment == "ALIGNED":
                mult = self.config['weight_multipliers']['aligned']['large']
            else:
                if not sweep_at_gap or retracement_pct < self.config['retracement_thresholds']['large_contra_min']:
                    verdict = "VETO"
                    reasoning += " | Contra-gap needs sweep + 30% retrace"
        elif cat == "extreme":
            # Hard veto first 15 min
            if curr_time_ist.time() < (pd.Timestamp("09:30:00").time()):
                verdict = "VETO"
                reasoning += " | Extreme gap blackout (09:15-09:30)"
            else:
                if alignment == "ALIGNED":
                    mult = self.config['weight_multipliers']['aligned']['extreme']
                else:
                    if not sweep_at_gap:
                        verdict = "VETO"
                        reasoning += " | Contra-extreme needs SMC sweep"

        return GapVerdict(
            verdict=verdict,
            gap_category=cat,
            gap_direction=gap_dir,
            gap_pct=gap_pct,
            gap_atr=gap_atr,
            historical_fill_probability=fill_prob,
            signal_alignment=alignment,
            weight_multiplier=mult,
            stock_vs_index_anomaly=False, # Handled by orchestrator
            reasoning=reasoning
        )
