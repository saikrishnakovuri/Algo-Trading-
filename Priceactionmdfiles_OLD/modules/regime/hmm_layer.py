import numpy as np
import pandas as pd
import joblib
import os
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from typing import List, Optional, Tuple, Dict

class HMMClassifier:
    """
    Layer 2: Probabilistic HMM-based market regime classification.
    """
    
    def __init__(self, model_path: str = "models/regime_hmm.joblib"):
        self.model_path = model_path
        self.model: Optional[GaussianHMM] = None
        self.scaler: Optional[StandardScaler] = None
        self.state_map: Dict[int, str] = {} # Maps hidden states to labels
        
        if os.path.exists(model_path):
            self.load()

    def train(self, data: pd.DataFrame, features: List[str]):
        """
        Trains the HMM on historical features.
        Features expected to be: [ADX_5m, Choppiness_5m, Hurst, RV_ratio, Range_ratio]
        """
        X = data[features].values
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = GaussianHMM(
            n_components=4, 
            covariance_type='full', 
            n_iter=1000, 
            random_state=42
        )
        self.model.fit(X_scaled)
        
        # Map states to labels based on stats
        self._map_states(data, features)
        self.save()

    def _map_states(self, data: pd.DataFrame, features: List[str]):
        X_scaled = self.scaler.transform(data[features].values)
        states = self.model.predict(X_scaled)
        
        temp_df = data.copy()
        temp_df['state'] = states
        
        state_stats = temp_df.groupby('state').agg({
            'ADX_5m': 'median',
            'Choppiness_5m': 'median',
            'RV_ratio': 'median'
        })
        
        # Heuristic Mapping
        # 1. Highest ADX + Lower Choppiness -> TRENDING_HIGH_VOL or LOW_VOL
        # 2. Highest Choppiness -> CHOPPY
        # 3. Lowest ADX + Mid Choppiness -> MEAN_REVERTING
        
        # This is a simplified mapping for the skeleton
        # In production, we'd use the logic from the brief
        sorted_by_adx = state_stats.sort_values('ADX_5m', ascending=False).index.tolist()
        sorted_by_chop = state_stats.sort_values('Choppiness_5m', ascending=False).index.tolist()
        
        self.state_map = {}
        # Assume highest ADX state is TRENDING_HIGH_VOL (if RV high) or LOW_VOL
        high_adx_state = sorted_by_adx[0]
        if state_stats.loc[high_adx_state, 'RV_ratio'] > 1.2:
            self.state_map[high_adx_state] = "TRENDING_HIGH_VOL"
        else:
            self.state_map[high_adx_state] = "TRENDING_LOW_VOL"
            
        # Highest Choppiness -> CHOPPY
        choppy_state = sorted_by_chop[0]
        if choppy_state not in self.state_map:
            self.state_map[choppy_state] = "CHOPPY_UNTRADEABLE"
            
        # Lowest ADX -> MEAN_REVERTING
        low_adx_state = sorted_by_adx[-1]
        if low_adx_state not in self.state_map:
            self.state_map[low_adx_state] = "MEAN_REVERTING"
            
        # Fill remaining
        labels = ["TRENDING_HIGH_VOL", "TRENDING_LOW_VOL", "MEAN_REVERTING", "CHOPPY_UNTRADEABLE"]
        for s in range(4):
            if s not in self.state_map:
                for lbl in labels:
                    if lbl not in self.state_map.values():
                        self.state_map[s] = lbl
                        break

    def predict(self, features: np.ndarray) -> Tuple[str, float]:
        """
        features: 1D array of [ADX_5m, Choppiness_5m, Hurst, RV_ratio, Range_ratio]
        Returns (regime_label, confidence)
        """
        if self.model is None or self.scaler is None:
            return "CHOPPY_UNTRADEABLE", 0.0
            
        X_scaled = self.scaler.transform(features.reshape(1, -1))
        state = self.model.predict(X_scaled)[0]
        
        # Confidence = posterior probability of the predicted state
        posteriors = self.model.predict_proba(X_scaled)[0]
        conf = posteriors[state]
        
        label = self.state_map.get(state, "CHOPPY_UNTRADEABLE")
        return label, float(conf)

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'state_map': self.state_map
        }, self.model_path)

    def load(self):
        data = joblib.load(self.model_path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.state_map = data['state_map']
