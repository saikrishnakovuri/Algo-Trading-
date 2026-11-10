import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path
from modules.risk_exec.schemas import SizingDecision, ApprovedSignal

class AdaptivePositionSizer:
    """
    Three-layer position sizer: Base Setup Risk + Fractional Kelly + Vol targeting.
    """
    
    def __init__(self, config: Dict[str, Any], trade_history_path: Path):
        self.config = config['sizing']
        self.trade_history_path = trade_history_path
        
    def calculate(self, signal: ApprovedSignal, current_equity: float, 
                  sl_price: float, stock_adv: float) -> SizingDecision:
        
        # 1. Base Risk from SMC Tier
        base_risk_pct = self.config['base_risk_pct'].get(signal.smc_tier, 0.35)
        
        # 2. Fractional Kelly multiplier
        kelly_mult = self._calculate_kelly_multiplier(signal.regime)
        
        # 3. Volatility targeting multiplier
        vol_mult = self._calculate_vol_multiplier()
        
        final_risk_pct = base_risk_pct * kelly_mult * vol_mult
        
        # Risk amount and shares
        risk_amount = current_equity * final_risk_pct / 100.0
        per_share_risk = abs(signal.entry_price - sl_price)
        
        if per_share_risk <= 0:
            return self._zero_decision("INVALID_SL")
            
        shares = int(risk_amount / per_share_risk)
        
        # 4. Constraints
        constraints_hit = []
        
        # Position Cap (20%)
        pos_cap = self.config['constraints']['position_cap_pct'] / 100.0
        max_order_value = current_equity * pos_cap
        if (shares * signal.entry_price) > max_order_value:
            shares = int(max_order_value / signal.entry_price)
            constraints_hit.append("position_cap")
            
        # Liquidity Cap (0.2% of ADV)
        liq_cap = self.config['constraints']['liquidity_cap_of_adv']
        max_liq_value = stock_adv * liq_cap
        if (shares * signal.entry_price) > max_liq_value:
            shares = int(max_liq_value / signal.entry_price)
            constraints_hit.append("liquidity_cap")
            
        if shares < 1:
            return self._zero_decision("UNTRADEABLE_SIZE")

        reasoning = (f"Base {base_risk_pct}% x Kelly {kelly_mult:.2f} x Vol {vol_mult:.2f} "
                     f"= {final_risk_pct:.2f}% risk.")
        if constraints_hit:
            reasoning += f" Caps hit: {', '.join(constraints_hit)}"

        return SizingDecision(
            shares=shares,
            final_risk_pct=round(final_risk_pct, 4),
            risk_amount=round(shares * per_share_risk, 2),
            components={'base': base_risk_pct, 'kelly_mult': kelly_mult, 'vol_mult': vol_mult},
            constraints_hit=constraints_hit,
            reasoning=reasoning
        )

    def _calculate_kelly_multiplier(self, regime: str) -> float:
        if not self.trade_history_path.exists():
            return 1.0
            
        try:
            if self.trade_history_path.suffix == '.parquet':
                df = pd.read_parquet(self.trade_history_path)
            else:
                df = pd.read_csv(self.trade_history_path)
            
            # FIX 1: Only include closed trades to avoid biasing sizing with open PnL
            if 'status' in df.columns:
                closed_df = df[df['status'] == 'CLOSED']
            else:
                # Fallback if status col missing: check if net_r is populated (non-zero or non-null)
                # but safer to require 'CLOSED' status.
                closed_df = df.dropna(subset=['net_r'])
                
            regime_df = closed_df[closed_df['regime'] == regime]
            
            if len(regime_df) < self.config['kelly']['min_trades_per_regime']:
                return 1.0
                
            # Expectancy = (WR * avg_win) - (LR * avg_loss) in R terms
            # Note: net_r should be stored in trade_history
            wins = regime_df[regime_df['net_r'] > 0]
            losses = regime_df[regime_df['net_r'] <= 0]
            
            win_rate = len(wins) / len(regime_df)
            avg_win_r = wins['net_r'].mean() if not wins.empty else 0
            avg_loss_r = abs(losses['net_r'].mean()) if not losses.empty else 1.0
            
            if avg_win_r <= 0: return self.config['kelly']['min_multiplier']
            
            expectancy = (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)
            kelly_f = expectancy / avg_win_r
            
            multiplier = 0.25 * kelly_f
            return float(np.clip(multiplier, 
                                 self.config['kelly']['min_multiplier'], 
                                 self.config['kelly']['max_multiplier']))
        except Exception:
            return 1.0

    def _calculate_vol_multiplier(self) -> float:
        # Vol targeting annualised 15%
        # Implementation needs daily PnL history. 
        # For now, return 1.0 as we haven't implemented daily PnL log yet.
        return 1.0

    def _zero_decision(self, reason: str) -> SizingDecision:
        return SizingDecision(0, 0.0, 0.0, {'base': 0.0, 'kelly_mult': 1.0, 'vol_mult': 1.0}, [], reason)
