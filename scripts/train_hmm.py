import pandas as pd
import numpy as np
import os
from modules.regime.hmm_layer import HMMClassifier

def generate_synthetic_data(n_bars=5000):
    np.random.seed(42)
    # Simulate features [ADX_5m, Choppiness_5m, Hurst, RV_ratio, Range_ratio]
    data = pd.DataFrame({
        'ADX_5m': np.concatenate([
            np.random.normal(35, 5, n_bars//4), # Trending High Vol
            np.random.normal(25, 3, n_bars//4), # Trending Low Vol
            np.random.normal(15, 2, n_bars//4), # Mean Reverting
            np.random.normal(10, 2, n_bars//4)  # Choppy
        ]),
        'Choppiness_5m': np.concatenate([
            np.random.normal(30, 5, n_bars//4),
            np.random.normal(40, 5, n_bars//4),
            np.random.normal(50, 5, n_bars//4),
            np.random.normal(70, 5, n_bars//4)
        ]),
        'RV_ratio': np.concatenate([
            np.random.normal(1.5, 0.2, n_bars//4),
            np.random.normal(1.0, 0.1, n_bars//4),
            np.random.normal(0.9, 0.1, n_bars//4),
            np.random.normal(0.8, 0.1, n_bars//4)
        ]),
        'Hurst': np.random.uniform(0.3, 0.7, n_bars),
        'Range_ratio': np.random.uniform(0.4, 2.0, n_bars)
    })
    return data

def main():
    print("🚀 Training HMM Layer with synthetic data...")
    data = generate_synthetic_data()
    features = ['ADX_5m', 'Choppiness_5m', 'Hurst', 'RV_ratio', 'Range_ratio']
    
    hmm = HMMClassifier(model_path="models/regime_hmm.joblib")
    hmm.train(data, features)
    
    print("✅ HMM Training Complete.")
    print(f"State Map: {hmm.state_map}")

if __name__ == "__main__":
    main()
