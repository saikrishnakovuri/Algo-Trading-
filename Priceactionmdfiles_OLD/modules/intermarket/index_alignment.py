import pandas as pd
import numpy as np
import yaml
from typing import Dict, Any, Optional, Tuple
from modules.intermarket.schemas import IndexContext, IndexAlignmentVerdict
from modules.intermarket.universe_mapper import SymbolUniverseMapper

class IndexAlignmentChecker:
    def __init__(self, config_path: str = "config/intermarket.yaml", universe_mapper: Optional[SymbolUniverseMapper] = None):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['index_alignment']
        self.mapper = universe_mapper or SymbolUniverseMapper()

    def get_bias_score(self, ohlcv: pd.DataFrame, lookback: int) -> int:
        if ohlcv is None or len(ohlcv) < lookback:
            return 0
        close = ohlcv['close'].iloc[-1]
        prev_close = ohlcv['close'].iloc[-lookback]
        return 1 if close > prev_close else -1 if close < prev_close else 0

    def get_avwap_bias(self, ohlcv: pd.DataFrame) -> int:
        # Assuming VolumeProfile logic: above VWAP = bullish
        # For simplicity, using simple VWAP if Module 2 not directly injected
        if ohlcv is None or 'Volume' not in ohlcv.columns:
            return 0
        typical_price = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3
        vwap = (typical_price * ohlcv['volume']).cumsum() / ohlcv['volume'].cumsum()
        current_vwap = vwap.iloc[-1]
        current_price = ohlcv['close'].iloc[-1]
        return 1 if current_price > current_vwap else -1

    def compute_index_state(self, ctx: IndexContext) -> Tuple[str, int]:
        # Robust None check
        if ctx is None or ctx.ohlcv_5m is None or len(ctx.ohlcv_5m) < 5:
            return "NEUTRAL", 0
            
        # 5m Trend: Last 5 bars (25 mins) progress
        current_close = ctx.ohlcv_5m['close'].iloc[-1]
        prev_close = ctx.ohlcv_5m['close'].iloc[-5]
        
        pct_change = (current_close - prev_close) / prev_close
        
        if pct_change >= 0.001: # +0.1% in 25 mins
            return "BULL", 1
        elif pct_change <= -0.001: # -0.1% in 25 mins
            return "BEAR", -1
            
        return "NEUTRAL", 0

    def evaluate(self, symbol: str, direction: str, nifty_ctx: IndexContext, 
                 banknifty_ctx: Optional[IndexContext] = None, 
                 smc_tier: str = "MINOR", index_sweep: bool = False) -> IndexAlignmentVerdict:
        
        nifty_state, n_val = self.compute_index_state(nifty_ctx)
        
        # Determine if it's a bank stock to check BankNifty
        FINANCIALS = ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'BAJFINANCE']
        is_financial = any(f in symbol for f in FINANCIALS)
        
        final_state = nifty_state
        final_val = n_val
        
        if is_financial and banknifty_ctx:
            bn_state, bn_val = self.compute_index_state(banknifty_ctx)
            # Use BankNifty as primary for financials
            final_state = bn_state
            final_val = bn_val

        # Alignment Logic with specific deltas
        alignment = "NEUTRAL"
        score_delta = 0.0
        veto = False
        
        # Direction: LONG = 1, SHORT = -1
        dir_val = 1 if direction == "LONG" else -1
        
        # Calculate alignment
        if final_val * dir_val > 0:
            alignment = "ALIGNED"
            score_delta = 0.0
        elif final_val * dir_val < 0:
            alignment = "CONTRA"
            score_delta = 0.0 # Softened penalty for fighting the index
            # We don't hard veto here to allow high-conviction traps
        else:
            alignment = "NEUTRAL"
            score_delta = 0.0
            
        reasoning = f"Nifty: {nifty_state} | Final State: {final_state} | Delta: {score_delta}"
        
        return IndexAlignmentVerdict(
            nifty_state=nifty_state,
            banknifty_state=final_state if is_financial else None,
            alignment=alignment,
            score_delta=score_delta,
            veto=veto,
            override_applied=None,
            reasoning=reasoning
        )
