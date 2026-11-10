import pandas as pd
import os
from typing import Dict, Any, Optional
from modules.regime.classifier import MarketRegimeClassifier
from modules.regime.schemas import RegimeDecision

class MarketRegimeAdapter:
    """
    Adapter to plug MarketRegimeClassifier into existing PriceActionEngine.
    """
    _bt_data_cache = {}
    
    def __init__(self, config_path: str = "config/regime.yaml", 
                 hmm_model_path: str = "models/regime_hmm.joblib"):
        self.classifier = MarketRegimeClassifier(config_path, hmm_model_path)
        
    def get_regime_decision(self, mtf_analyses: Dict[str, Any], backtest_mode: bool = False) -> RegimeDecision:
        """
        Extracts required data from mtf_analyses or external sources 
        to perform classification.
        """
        df_5m = mtf_analyses.get('5m')
        df_15m = mtf_analyses.get('15m')

        if df_5m is None or df_15m is None:
            return self._default_choppy()

        # FIX: Check for feeds with backtest fallback
        india_vix = mtf_analyses.get('india_vix')
        vix_history_5d = mtf_analyses.get('vix_history_5d')
        df_nifty_daily = mtf_analyses.get('nifty_daily')

        if backtest_mode:
            # OPTIMIZATION: Use cached daily data to avoid repeated disk reads
            try:
                if 'vix' not in MarketRegimeAdapter._bt_data_cache:
                    if os.path.exists("data/india_vix_daily.csv"):
                        MarketRegimeAdapter._bt_data_cache['vix'] = pd.read_csv("data/india_vix_daily.csv", index_col=0, parse_dates=True)
                    else:
                        MarketRegimeAdapter._bt_data_cache['vix'] = pd.DataFrame()
                        
                if 'nifty' not in MarketRegimeAdapter._bt_data_cache:
                    if os.path.exists("data/nifty50_daily.csv"):
                        MarketRegimeAdapter._bt_data_cache['nifty'] = pd.read_csv("data/nifty50_daily.csv", index_col=0, parse_dates=True)
                    else:
                        MarketRegimeAdapter._bt_data_cache['nifty'] = pd.DataFrame()

                vix_df = MarketRegimeAdapter._bt_data_cache['vix']
                nifty_df = MarketRegimeAdapter._bt_data_cache['nifty']
                
                # Use index of current bar to find session date
                current_date = df_5m.index[-1].normalize()
                if current_date.tz is not None:
                    current_date = current_date.tz_localize(None)
                
                if not vix_df.empty:
                    if vix_df.index.tz is not None:
                        vix_df.index = vix_df.index.tz_localize(None)
                    # Use last available before current_date (inclusive)
                    valid_vix = vix_df[:current_date]
                    if not valid_vix.empty:
                        india_vix = valid_vix['close'].iloc[-1]
                        vix_history_5d = valid_vix['close'].tail(5)
                
                if not nifty_df.empty:
                    if nifty_df.index.tz is not None:
                        nifty_df.index = nifty_df.index.tz_localize(None)
                    df_nifty_daily = nifty_df[:current_date]
            except Exception as e:
                print(f"⚠️ Error loading real regime data: {e}. Using fallbacks.")

            # Fallback for backtest mode to allow baseline run
            if india_vix is None: india_vix = 15.0
            if vix_history_5d is None: vix_history_5d = pd.Series([15.0] * 5)
            if df_nifty_daily is None: df_nifty_daily = df_5m.resample('D').last().dropna()
        elif any(v is None for v in [india_vix, vix_history_5d, df_nifty_daily]):
            raise ValueError(
                "India VIX and Nifty Daily data feeds not configured. "
                "Module 1 requires volatility and macro trend context for classification."
            )

        return self.classifier.classify(
            df_5m, df_15m, india_vix, vix_history_5d, df_nifty_daily
        )
    
    def _default_choppy(self) -> RegimeDecision:
        return RegimeDecision(
            regime="CHOPPY_UNTRADEABLE",
            confidence=1.0,
            allow_trades=False,
            param_overrides={"allow_trades": False},
            feature_snapshot={},
            reasoning="Missing Input Data",
        )

    @staticmethod
    def apply_overrides(base_config: Dict[str, Any], decision: RegimeDecision) -> Dict[str, Any]:
        """
        Merges regime overrides into the base config of PriceActionEngine.
        """
        if not decision.allow_trades:
            return {**base_config, "allow_trades": False}
            
        overrides = decision.param_overrides
        new_config = base_config.copy()
        
        # Mapping param_overrides keys to PriceActionEngine internal keys
        if "min_score_delta" in overrides:
            # Assuming PriceActionEngine uses a 'min_score' base
            new_config['min_score'] = base_config.get('min_score', 5.0) + overrides['min_score_delta']
            
        if "sl_multiplier" in overrides:
            new_config['sl_multiplier'] = overrides['sl_multiplier']
            
        if "tp_multipliers" in overrides:
            new_config['tp_multipliers'] = overrides['tp_multipliers']
            
        return new_config
