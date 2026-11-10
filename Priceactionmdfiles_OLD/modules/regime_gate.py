import yaml
import logging
import pandas as pd
from datetime import datetime
from modules.regime.classifier import MarketRegimeClassifier

logger = logging.getLogger('live_trader')

class RegimeGate:
    def __init__(self, config_path="config/regime_gating.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)['regime_gating']
        
        self.classifier = MarketRegimeClassifier()
        self.current_regime = "UNKNOWN"
        self.regime_history = []
        self.last_update_bar = 0
        self.regime_change_cooldown = 0

    def update_regime(self, df_index: pd.DataFrame) -> str:
        """Evaluates current market regime using NIFTY 50 data."""
        if not self.config['enabled']:
            self.current_regime = "TRENDING_UP" # Default
            return self.current_regime

        try:
            # Call existing classifier
            regime_state = self.classifier.classify(df_index)
            raw_regime = regime_state.regime if hasattr(regime_state, 'regime') else str(regime_state)
            
            # Map Classifier regimes to Gate permissions
            mapping = {
                "TRENDING_HIGH_VOL": "VOLATILE",
                "TRENDING_LOW_VOL": "TRENDING_UP",
                "MEAN_REVERTING": "RANGING",
                "CHOPPY_UNTRADEABLE": "CHOPPY"
            }
            new_regime = mapping.get(raw_regime, "RANGING")
            
            # Stability filter: requires 3 consecutive readings for change
            self.regime_history.append(new_regime)
            if len(self.regime_history) > 3:
                self.regime_history.pop(0)
            
            if len(self.regime_history) == 3 and all(r == new_regime for r in self.regime_history):
                if new_regime != self.current_regime:
                    print(f"[REGIME] CHANGE: {self.current_regime} -> {new_regime}")
                    logger.info(f"[REGIME] CHANGE: {self.current_regime} -> {new_regime}")
                    self.current_regime = new_regime
                    self.regime_change_cooldown = self.config['transitions']['cooldown_after_change_bars']
            
            # print(f"DEBUG REGIME: {new_regime} (Stable: {self.current_regime})")
            
            if self.regime_change_cooldown > 0:
                self.regime_change_cooldown -= 1
                
        except Exception as e:
            logger.error(f"REGIME_ERROR: {e}")
            if self.current_regime == "UNKNOWN":
                self.current_regime = "RANGING" # Safe fallback
        
        return self.current_regime

    def is_strategy_allowed(self, strategy_name: str) -> bool:
        if not self.config['enabled']: return True
        if self.regime_change_cooldown > 0: return False
        
        perm = self.config['permissions'].get(self.current_regime, {})
        strat_perm = perm.get(strategy_name, {})
        return strat_perm.get('enabled', True)

    def get_confidence_adjustment(self, strategy_name: str) -> int:
        perm = self.config['permissions'].get(self.current_regime, {}).get(strategy_name, {})
        boost = perm.get('confidence_boost', 0)
        penalty = perm.get('confidence_penalty', 0)
        return boost - penalty

    def get_max_positions(self) -> int:
        return self.config['permissions'].get(self.current_regime, {}).get('max_positions', 10)

    def get_risk_override(self) -> float:
        return self.config['permissions'].get(self.current_regime, {}).get('risk_per_trade_override')
