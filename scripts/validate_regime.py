import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from modules.regime.classifier import MarketRegimeClassifier

def generate_validation_data(n_bars=2000):
    """
    Simulates a sequence of market data with known shifts.
    """
    np.random.seed(42)
    # Price
    price = 18000 + np.cumsum(np.random.normal(0, 5, n_bars))
    dates = pd.date_range(start="2023-01-01", periods=n_bars, freq="5min")
    
    # Features (Mocked)
    adx = np.concatenate([
        np.random.normal(30, 5, n_bars//4), # Trend
        np.random.normal(15, 2, n_bars//2), # Range
        np.random.normal(30, 5, n_bars//4)  # Trend
    ])
    
    chop = np.concatenate([
        np.random.normal(35, 5, n_bars//4),
        np.random.normal(50, 5, n_bars//2),
        np.random.normal(35, 5, n_bars//4)
    ])
    
    data = pd.DataFrame({
        'High': price + 2,
        'Low': price - 2,
        'Close': price,
        'Volume': np.random.randint(1000, 5000, n_bars),
        'ADX_5m': adx,
        'Choppiness_5m': chop,
        'Hurst': 0.5,
        'RV_ratio': 1.0,
        'Range_ratio': 1.0
    }, index=dates)
    
    return data

def validate_regime_labels(classifier, data):
    print("📋 1. Backtesting Regime Labels...")
    regimes = []
    
    # Mock Nifty Daily and 15m
    nifty_daily = data.resample('D').last().dropna()
    vix_hist = pd.Series([15.0] * 5)
    
    for i in range(200, len(data), 50):
        chunk_5m = data.iloc[i-200:i]
        chunk_15m = chunk_5m.iloc[::3]
        
        decision = classifier.classify(chunk_5m, chunk_15m, 15.0, vix_hist, nifty_daily)
        regimes.append(decision.regime)
        
    unique, counts = np.unique(regimes, return_counts=True)
    print(f"   Distribution: {dict(zip(unique, counts))}")
    return regimes

def check_transition_stability(regimes):
    print("📋 2. Checking Transition Matrix Stability...")
    regime_to_id = {
        "TRENDING_HIGH_VOL": 0, "TRENDING_LOW_VOL": 1, 
        "MEAN_REVERTING": 2, "CHOPPY_UNTRADEABLE": 3
    }
    
    matrix = np.zeros((4, 4))
    for i in range(len(regimes)-1):
        s1 = regime_to_id.get(regimes[i], 3)
        s2 = regime_to_id.get(regimes[i+1], 3)
        matrix[s1, s2] += 1
        
    # Normalize rows
    row_sums = matrix.sum(axis=1)
    
    # Only consider rows that actually had transitions
    active_rows = np.where(row_sums > 0)[0]
    if len(active_rows) == 0:
        return True # No transitions to evaluate
        
    diagonals = []
    for r in active_rows:
        diagonals.append(matrix[r, r] / row_sums[r])
    
    diagonal_avg = np.mean(diagonals)
    print(f"   Average Diagonal (Stability) for active regimes: {diagonal_avg:.2f}")
    
    if diagonal_avg < 0.7:
        print("   ⚠️ WARNING: Transitions are unstable (flipping too much).")
        return False
    else:
        print("   ✅ Stability check passed.")
        return True

def main():
    print("🚀 Starting Module 1 Validation Protocol...")
    
    classifier = MarketRegimeClassifier()
    data = generate_validation_data()
    
    regimes = validate_regime_labels(classifier, data)
    stability_pass = check_transition_stability(regimes)
    
    if stability_pass:
        print("\n🎉 MODULE 1: READY (Pending full A/B Backtest results)")
    else:
        print("\n❌ VALIDATION FAILED")

if __name__ == "__main__":
    main()
