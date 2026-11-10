import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from modules.risk_exec.engine import RiskTradeManagementEngine
from modules.risk_exec.schemas import ApprovedSignal, MarketContext, OpenPosition

class RiskExecAdapter:
    """
    Adapter to plug RiskTradeManagementEngine into PriceActionEngine.
    """
    
    def __init__(self, config_path: str = "config/risk_execution.yaml"):
        self.engine = RiskTradeManagementEngine(config_path)
        
    def build_approved_signal(self, symbol: str, signal_dict: Dict[str, Any], 
                              mtf_analyses: Dict[str, Any], regime: str) -> ApprovedSignal:
        
        return ApprovedSignal(
            symbol=symbol,
            direction="LONG" if signal_dict['trade'] == 'CE' else "SHORT",
            entry_price=signal_dict['entry'],
            setup_type=signal_dict.get('setup', 'OTHER'),
            raw_score=signal_dict.get('checklist_score', 0),
            smc_tier=signal_dict.get('smc_metadata', {}).tier_label if 'smc_metadata' in signal_dict else "MINOR",
            vp_tier="NORMAL", # Placeholder
            regime=regime,
            signal_ts=signal_dict.get('signal_ts', datetime.now()),
            metadata=signal_dict
        )

    def build_market_context(self, symbol: str, mtf_analyses: Dict[str, Any], 
                             regime_decision: Any, vp_levels: Any, 
                             smc_state: Any, active_window: str, 
                             prior_ohlc: Dict[str, float]) -> MarketContext:
        
        from modules.price_action_engine import PriceActionEngine
        atr_5m = PriceActionEngine.calculate_atr(mtf_analyses.get('5m'))
        
        return MarketContext(
            atr_5m=atr_5m,
            liquidity_tier="high_liquidity" if symbol in ["RELIANCE", "HDFCBANK", "TCS"] else "medium_liquidity",
            regime=regime_decision.regime,
            level_set=vp_levels,
            smc_state=smc_state,
            active_window=active_window,
            stock_adv=1e9, # Placeholder
            prior_session_ohlc=prior_ohlc
        )
