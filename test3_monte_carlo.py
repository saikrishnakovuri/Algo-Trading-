"""
OOS Validation - Test 3: Monte Carlo Shuffle
"""
import pandas as pd
import numpy as np
import json

# CONFIG
RESULTS_DIR = "data/backtest_results/oos_validation"

def main():
    try:
        df = pd.read_csv(f"{RESULTS_DIR}/test_trades.csv")
    except:
        print("Run test1_oos.py first.")
        return
        
    real_r = df['R_Multiple'].values
    real_exp = real_r.mean()
    
    print(f"MONTE CARLO SHUFFLE TEST")
    print(f"Real OOS Expectancy: {real_exp:+.4f}R")
    
    # Shuffle Test
    n = 1000
    shuffled_exps = []
    for _ in range(n):
        shuffled_exps.append(np.random.permutation(real_r).mean())
        
    # Since shuffle uses SAME values, mean is identical. 
    # Better: Random entry simulation (Coin flip direction)
    random_exps = []
    for _ in range(n):
        # Randomly flip signs of R-multiples
        random_r = np.where(np.random.random(len(real_r)) > 0.5, np.abs(real_r), -np.abs(real_r))
        random_exps.append(random_r.mean())
        
    p_val = np.sum(np.array(random_exps) >= real_exp) / n
    
    print(f"Random 50/50 Entry p-value: {p_val:.4f}")
    print(f"Significant (p < 0.05): {'YES ✓' if p_val < 0.05 else 'NO ✗'}")
    
    with open(f"{RESULTS_DIR}/monte_carlo.json", "w") as f:
        json.dump({'p_value': p_val, 'real_exp': real_exp}, f)

if __name__ == "__main__":
    main()
