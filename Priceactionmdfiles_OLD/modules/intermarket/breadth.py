import pandas as pd
import numpy as np
import yaml
from typing import Dict, Any, List, Optional
from modules.intermarket.schemas import BreadthVerdict, UniverseSnapshot

class BreadthEngine:
    def __init__(self, config_path: str = "config/intermarket.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['breadth']

    def evaluate(self, direction: str, universe_snapshot: UniverseSnapshot, candidate_symbol: Optional[str] = None) -> BreadthVerdict:
        snaps = universe_snapshot.symbol_snapshots
        if not snaps:
            return BreadthVerdict("NEUTRAL", 1.0, 1.0, 50.0, None, 0.0, "No data")
            
        advancers = 0
        decliners = 0
        up_vol = 0.0
        down_vol = 0.0
        above_vwap_count = 0
        
        filtered_count = 0
        for sym, snap in snaps.items():
            # FIX 2: Exclude candidate symbol to prevent circular self-reference
            if candidate_symbol and sym == candidate_symbol:
                continue
                
            s_open = snap.get('open')
            s_close = snap.get('close')
            s_vol = snap.get('volume', 0)
            s_vwap = snap.get('vwap')
            
            if s_open and s_close:
                if s_close > s_open:
                    advancers += 1
                    up_vol += s_vol
                else:
                    decliners += 1
                    down_vol += s_vol
                
                if s_vwap and s_close > s_vwap:
                    above_vwap_count += 1
                    
        total = len(snaps)
        adr = advancers / decliners if decliners > 0 else (advancers if advancers > 0 else 1.0)
        up_vol_ratio = up_vol / down_vol if down_vol > 0 else (up_vol if up_vol > 0 else 1.0)
        pct_above_vwap = (above_vwap_count / total * 100) if total > 0 else 50.0
        
        # Classification
        regime = "NEUTRAL"
        c = self.config
        
        if adr >= c['bullish_broad']['adr'] and up_vol_ratio >= c['bullish_broad']['up_vol'] and pct_above_vwap >= c['bullish_broad']['pct_above_vwap']:
            regime = "BULLISH_BROAD"
        elif adr >= c['bullish']['adr'] and up_vol_ratio >= c['bullish']['up_vol']:
            regime = "BULLISH"
        elif adr <= c['bearish_broad']['adr'] and up_vol_ratio <= (1/c['bearish_broad']['down_vol']) and pct_above_vwap <= c['bearish_broad']['pct_above_vwap']:
            regime = "BEARISH_BROAD"
        elif adr <= c['bearish']['adr']:
            regime = "BEARISH"

        # Scoring
        score_delta = 0.0
        if direction == "LONG":
            if regime == "BULLISH_BROAD": score_delta = c['score_deltas']['aligned_broad']
            elif regime == "BULLISH": score_delta = c['score_deltas']['aligned_regular']
            elif regime == "BEARISH_BROAD": score_delta = c['score_deltas']['opposes_broad']
        else: # SHORT
            if regime == "BEARISH_BROAD": score_delta = c['score_deltas']['aligned_broad']
            elif regime == "BEARISH": score_delta = c['score_deltas']['aligned_regular']
            elif regime == "BULLISH_BROAD": score_delta = c['score_deltas']['opposes_broad']

        reasoning = f"Regime: {regime} | ADR: {adr:.2f} | VolRatio: {up_vol_ratio:.2f} | %AboveVWAP: {pct_above_vwap:.1f}%"
        
        return BreadthVerdict(
            regime=regime,
            adr=adr,
            up_vol_ratio=up_vol_ratio,
            pct_above_vwap=pct_above_vwap,
            divergence=None,
            score_delta=score_delta,
            reasoning=reasoning
        )
