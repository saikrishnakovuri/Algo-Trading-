from datetime import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from modules.regime.schemas import RegimeDecision
from modules.regime.rule_layer import RuleBasedClassifier
from modules.regime.hmm_layer import HMMClassifier
from modules.regime.features import FeatureCalculator

class MarketRegimeClassifier:
    """
    Two-layer ensemble classifier for market regimes.
    """
    
    def __init__(self, config_path: str = "config/regime.yaml", 
                 hmm_model_path: str = "models/regime_hmm.joblib"):
        self.rule_layer = RuleBasedClassifier(config_path)
        self.hmm_layer = HMMClassifier(hmm_model_path)
        # Transition Stability Smoothing
        self._history: List[str] = []
        self._current_stable_regime: Optional[str] = None
        
    def classify(
        self, 
        df_5m: pd.DataFrame, 
        df_15m: pd.DataFrame = None, 
        india_vix: float = 15.0, 
        vix_history_5d: pd.Series = None,
        df_nifty_daily: pd.DataFrame = None
    ) -> RegimeDecision:
        """
        Final ensemble decision rule with 3-bar transition smoothing.
        """
        if df_15m is None: df_15m = df_5m
        if vix_history_5d is None: vix_history_5d = pd.Series([india_vix] * 10)
        if df_nifty_daily is None: df_nifty_daily = df_5m

        # 1. Compute features
        features = FeatureCalculator.get_feature_snapshot(
            df_5m, df_15m, india_vix, vix_history_5d, df_nifty_daily
        )
        
        # 2. Rule Layer
        rule_decision = self.rule_layer.classify(features)
        
        # 3. HMM Layer
        hmm_features = np.array([
            features['ADX_5m'], 
            features['Choppiness_5m'], 
            features['Hurst_exponent'], 
            features['RV_ratio'], 
            features['Range_ratio']
        ])
        hmm_regime, hmm_conf = self.hmm_layer.predict(hmm_features)
        
        # 4. Ensemble
        raw_regime = rule_decision.regime
        
        if rule_decision.regime == hmm_regime:
            final_conf = max(rule_decision.confidence, hmm_conf)
            reasoning = f"Ensemble Agreement: {rule_decision.reasoning} | HMM Conf: {hmm_conf:.2f}"
        else:
            if rule_decision.regime == "CHOPPY_UNTRADEABLE" or hmm_regime == "CHOPPY_UNTRADEABLE":
                raw_regime = "CHOPPY_UNTRADEABLE"
                final_conf = 1.0
                reasoning = f"Safety First: One layer detected CHOPPY (Rule: {rule_decision.regime}, HMM: {hmm_regime})"
            else:
                raw_regime = rule_decision.regime
                final_conf = rule_decision.confidence * 0.7
                reasoning = f"Disagreement (HMM suggested {hmm_regime}). Rule layer priority with penalty."

        # 5. Stability Smoothing (3-bar lock)
        self._history.append(raw_regime)
        if len(self._history) > 3: self._history.pop(0)
        
        if self._current_stable_regime is None:
            self._current_stable_regime = raw_regime
            
        # Change only if last 3 bars are identical and different from current
        if len(self._history) == 3 and all(x == self._history[0] for x in self._history):
            if self._history[0] != self._current_stable_regime:
                self._current_stable_regime = self._history[0]
                reasoning += f" | ⚡ Regime Transition to {self._current_stable_regime}"

        final_regime = self._current_stable_regime
        
        # Merge Overrides
        allow_trades = True
        overrides = self.rule_layer.config['overrides'].get(final_regime, {})
        
        if final_regime == "CHOPPY_UNTRADEABLE":
            allow_trades = False
            overrides = self.rule_layer.config['overrides']['CHOPPY_UNTRADEABLE']

        return RegimeDecision(
            regime=final_regime,
            confidence=float(final_conf),
            allow_trades=allow_trades,
            param_overrides=overrides,
            feature_snapshot=features,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
