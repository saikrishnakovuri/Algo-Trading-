import pandas as pd
import numpy as np
import yaml
from typing import Dict, Any, List, Optional
from modules.intermarket.schemas import RelativeStrengthVerdict
from modules.intermarket.universe_mapper import SymbolUniverseMapper

class RelativeStrengthScorer:
    def __init__(self, config_path: str = "config/intermarket.yaml", universe_mapper: Optional[SymbolUniverseMapper] = None):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['rs']
        self.mapper = universe_mapper or SymbolUniverseMapper()

    def compute_rs_value(self, stock_ret: float, nifty_ret: float, beta: float) -> float:
        # beta-adjusted RS = stock_return - (nifty_return * beta)
        return stock_ret - (nifty_ret * beta)

    def evaluate(self, symbol: str, direction: str, 
                 stock_ohlcv_session: pd.DataFrame, 
                 nifty_df: pd.DataFrame,
                 universe_snapshot: Any, # UniverseSnapshot dataclass
                 smc_tier: str = "MINOR") -> RelativeStrengthVerdict:
        
        if stock_ohlcv_session is None or len(stock_ohlcv_session) < 1 or nifty_df is None or len(nifty_df) < 1:
            return RelativeStrengthVerdict(rs_values={"session": 0.0}, rs_percentiles={"session": 50.0}, classification="NEUTRAL", rs_momentum_aligned=False, score_delta=0.0, veto=False, reasoning="Insufficient data for RS")

        beta = self.mapper.get_beta(symbol)
        
        # Horizons
        # session_return since today's open
        n_open = nifty_df['open'].iloc[0]
        n_curr = nifty_df['close'].iloc[-1]
        n_ret_session = (n_curr - n_open) / n_open
        
        s_open = stock_ohlcv_session['open'].iloc[0]
        s_curr = stock_ohlcv_session['close'].iloc[-1]
        s_ret_session = (s_curr - s_open) / s_open
        
        rs_session = self.compute_rs_value(s_ret_session, n_ret_session, beta)
        
        # RS Percentile (using universe_snapshot)
        # We compute RS for all symbols in universe and find our rank
        all_rs_values = []
        for sym, snap in universe_snapshot.symbol_snapshots.items():
            b = self.mapper.get_beta(sym)
            sn_open = snap['open']
            sn_curr = snap['close']
            if sn_open and sn_curr:
                sn_ret = (sn_curr - sn_open) / sn_open
                all_rs_values.append(self.compute_rs_value(sn_ret, n_ret_session, b))
        
        rs_pct_session = 50.0
        if all_rs_values:
            rs_pct_session = (sum(1 for x in all_rs_values if rs_session > x) / len(all_rs_values)) * 100

        # Classification
        classification = "NEUTRAL"
        if rs_pct_session >= self.config['strong_threshold_pct']:
            classification = "STRONG"
            if rs_pct_session >= self.config['super_strong_thresholds']['session_pct']:
                classification = "SUPER_STRONG"
        elif rs_pct_session <= self.config['weak_threshold_pct']:
            classification = "WEAK"
            if rs_pct_session <= self.config['super_weak_thresholds']['session_pct']:
                classification = "SUPER_WEAK"

        # Scoring
        score_delta = 0.0
        veto = False
        
        if direction == "LONG":
            if classification == "SUPER_STRONG": score_delta = self.config['score_deltas']['super_strong_aligned']
            elif classification == "STRONG": score_delta = self.config['score_deltas']['strong_aligned']
            elif classification == "WEAK": score_delta = self.config['score_deltas']['weak_contra_to_candidate']
            elif classification == "SUPER_WEAK":
                score_delta = self.config['score_deltas']['super_weak_contra_to_candidate']
                if smc_tier not in ["ELITE", "MONEY"]:
                    veto = True
        else: # SHORT
             if classification == "SUPER_WEAK": score_delta = self.config['score_deltas']['super_strong_aligned'] # aligned with short
             elif classification == "WEAK": score_delta = self.config['score_deltas']['strong_aligned']
             elif classification == "STRONG": score_delta = self.config['score_deltas']['weak_contra_to_candidate']
             elif classification == "SUPER_STRONG":
                score_delta = self.config['score_deltas']['super_weak_contra_to_candidate']
                if smc_tier not in ["ELITE", "MONEY"]:
                    veto = True

        reasoning = f"RS Session: {rs_session*100:.2f}% | Pct: {rs_pct_session:.1f} | Class: {classification} | Beta: {beta:.2f}"
        
        return RelativeStrengthVerdict(
            rs_values={"session": rs_session},
            rs_percentiles={"session": rs_pct_session},
            classification=classification,
            rs_momentum_aligned=False, # Placeholder
            score_delta=score_delta,
            veto=veto,
            reasoning=reasoning
        )
