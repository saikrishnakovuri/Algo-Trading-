"""
MONTE CARLO STRESS TEST
========================
10,000 randomized equity curve simulations using real trade data.

Reads: FINAL_PRODUCTION_CONFIG.json + all phase results CSVs
Outputs: MONTE_CARLO_REPORT.md + monte_carlo_results.json

Usage:
    python monte_carlo_stress.py
    python monte_carlo_stress.py --capital 500000 --target-roi 70 --months 12
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_CONFIG = {
    'capital': 500000,
    'target_roi_pct': 70,          # Target: 70% ROI
    'simulation_months': 12,        # Simulate 12 months forward
    'n_simulations': 10000,         # 10,000 random paths
    'ruin_threshold_pct': 50,       # Ruin = losing 50% of capital
    'risk_levels_to_test': [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0],  # % risk per trade
    'trades_per_month_estimate': None,  # Auto-calculated from data
}


# ============================================================
# DATA LOADING
# ============================================================

def load_survivor_trades():
    """Load trades from all phases, filtered to survivor strategies only."""
    
    # Load production config to get survivor strategies
    config_path = 'pipeline/results/FINAL_PRODUCTION_CONFIG.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            prod_config = json.load(f)
        survivor_strategies = set(prod_config.get('strategies', []))
    else:
        print("WARNING: FINAL_PRODUCTION_CONFIG.json not found. Using all trades.")
        survivor_strategies = None
    
    # Load all phase results
    all_trades = []
    for phase in range(2, 7):
        for pattern in [f'pipeline/results/phase{phase}_results.csv', f'pipeline/results/phase{phase}_raw_results.csv']:
            if os.path.exists(pattern):
                try:
                    df = pd.read_csv(pattern)
                    all_trades.append(df)
                    break
                except pd.errors.EmptyDataError:
                    continue
    
    if not all_trades:
        print("ERROR: No phase result files found!")
        sys.exit(1)
    
    combined = pd.concat(all_trades, ignore_index=True)
    
    # Filter to survivors only
    if survivor_strategies:
        combined = combined[combined['strategy_name'].isin(survivor_strategies)]
    
    print(f"Loaded {len(combined)} survivor trades from {len(all_trades)} phases")
    return combined


def extract_pnl_distribution(trades_df, capital=500000):
    """
    Extract the P&L per trade as a percentage of capital.
    This is the distribution we'll sample from in Monte Carlo.
    """
    pnl_pcts = (trades_df['pnl'] / capital * 100).values
    
    print(f"  P&L Distribution:")
    print(f"    Trades: {len(pnl_pcts)}")
    print(f"    Mean P&L: {np.mean(pnl_pcts):.4f}%")
    print(f"    Median P&L: {np.median(pnl_pcts):.4f}%")
    print(f"    Std Dev: {np.std(pnl_pcts):.4f}%")
    print(f"    Min: {np.min(pnl_pcts):.4f}%")
    print(f"    Max: {np.max(pnl_pcts):.4f}%")
    print(f"    Skewness: {pd.Series(pnl_pcts).skew():.2f}")
    print(f"    Kurtosis: {pd.Series(pnl_pcts).kurtosis():.2f}")
    
    return pnl_pcts


# ============================================================
# MONTE CARLO ENGINE
# ============================================================

def run_monte_carlo(
    pnl_distribution: np.ndarray,
    capital: float,
    n_simulations: int,
    trades_per_sim: int,
    risk_multiplier: float = 1.0,
    ruin_threshold_pct: float = 50,
) -> Dict:
    """
    Run N Monte Carlo simulations.
    
    Each simulation:
    1. Start with `capital`
    2. Randomly sample `trades_per_sim` trades from the P&L distribution
    3. Apply each trade's P&L (scaled by risk_multiplier)
    4. Track equity curve, drawdown, final capital
    
    Returns comprehensive statistics.
    """
    
    final_capitals = np.zeros(n_simulations)
    max_drawdowns = np.zeros(n_simulations)
    max_drawdown_durations = np.zeros(n_simulations)
    ruin_count = 0
    target_hit_count = 0
    double_count = 0
    time_to_target = []
    time_to_double = []
    
    target_capital = capital * 1.70  # 70% ROI
    double_capital = capital * 2.0
    ruin_capital = capital * (1 - ruin_threshold_pct / 100)
    
    # Store a few sample equity curves for visualization
    sample_curves = []
    
    for sim in range(n_simulations):
        # Random sample of trades
        sampled_pnls = np.random.choice(pnl_distribution, size=trades_per_sim, replace=True)
        
        # Scale by risk multiplier
        scaled_pnls = sampled_pnls * risk_multiplier
        
        equity = capital
        peak = capital
        max_dd = 0
        dd_start = 0
        max_dd_dur = 0
        current_dd_dur = 0
        hit_target = False
        hit_double = False
        ruined = False
        
        curve = [capital] if sim < 20 else None  # Store first 20 curves
        
        for t, pnl_pct in enumerate(scaled_pnls):
            pnl_amount = equity * (pnl_pct / 100)
            equity += pnl_amount
            
            if curve is not None:
                curve.append(equity)
            
            # Track peak and drawdown
            if equity > peak:
                peak = equity
                current_dd_dur = 0
            else:
                current_dd_dur += 1
                dd = (peak - equity) / peak * 100
                if dd > max_dd:
                    max_dd = dd
                if current_dd_dur > max_dd_dur:
                    max_dd_dur = current_dd_dur
            
            # Check milestones
            if not hit_target and equity >= target_capital:
                hit_target = True
                time_to_target.append(t + 1)
            
            if not hit_double and equity >= double_capital:
                hit_double = True
                time_to_double.append(t + 1)
            
            # Check ruin
            if equity <= ruin_capital:
                ruined = True
                ruin_count += 1
                break
        
        final_capitals[sim] = equity
        max_drawdowns[sim] = max_dd
        max_drawdown_durations[sim] = max_dd_dur
        
        if hit_target:
            target_hit_count += 1
        if hit_double:
            double_count += 1
        
        if curve is not None:
            sample_curves.append(curve)
    
    # Compile results
    results = {
        'config': {
            'capital': capital,
            'n_simulations': n_simulations,
            'trades_per_simulation': trades_per_sim,
            'risk_multiplier': risk_multiplier,
            'effective_risk_pct': round(risk_multiplier * 1.0, 2),  # Base is 1%
        },
        
        'final_capital': {
            'mean': round(np.mean(final_capitals), 2),
            'median': round(np.median(final_capitals), 2),
            'std': round(np.std(final_capitals), 2),
            'p5': round(np.percentile(final_capitals, 5), 2),
            'p10': round(np.percentile(final_capitals, 10), 2),
            'p25': round(np.percentile(final_capitals, 25), 2),
            'p50': round(np.percentile(final_capitals, 50), 2),
            'p75': round(np.percentile(final_capitals, 75), 2),
            'p90': round(np.percentile(final_capitals, 90), 2),
            'p95': round(np.percentile(final_capitals, 95), 2),
            'p99': round(np.percentile(final_capitals, 99), 2),
            'min': round(np.min(final_capitals), 2),
            'max': round(np.max(final_capitals), 2),
        },
        
        'roi': {
            'mean_pct': round((np.mean(final_capitals) - capital) / capital * 100, 2),
            'median_pct': round((np.median(final_capitals) - capital) / capital * 100, 2),
            'p5_pct': round((np.percentile(final_capitals, 5) - capital) / capital * 100, 2),
            'p95_pct': round((np.percentile(final_capitals, 95) - capital) / capital * 100, 2),
        },
        
        'probabilities': {
            'profit': round((final_capitals > capital).mean() * 100, 2),
            'target_70pct_roi': round(target_hit_count / n_simulations * 100, 2),
            'double_capital': round(double_count / n_simulations * 100, 2),
            'ruin': round(ruin_count / n_simulations * 100, 2),
            'lose_10pct': round((final_capitals < capital * 0.9).mean() * 100, 2),
            'lose_20pct': round((final_capitals < capital * 0.8).mean() * 100, 2),
            'lose_30pct': round((final_capitals < capital * 0.7).mean() * 100, 2),
            'gain_50pct': round((final_capitals > capital * 1.5).mean() * 100, 2),
            'gain_100pct': round((final_capitals > capital * 2.0).mean() * 100, 2),
            'gain_200pct': round((final_capitals > capital * 3.0).mean() * 100, 2),
        },
        
        'drawdown': {
            'mean_max_dd_pct': round(np.mean(max_drawdowns), 2),
            'median_max_dd_pct': round(np.median(max_drawdowns), 2),
            'p95_max_dd_pct': round(np.percentile(max_drawdowns, 95), 2),
            'p99_max_dd_pct': round(np.percentile(max_drawdowns, 99), 2),
            'worst_dd_pct': round(np.max(max_drawdowns), 2),
            'mean_dd_duration_trades': round(np.mean(max_drawdown_durations), 1),
            'max_dd_duration_trades': int(np.max(max_drawdown_durations)),
        },
        
        'time_to_milestone': {
            'target_70pct_roi': {
                'mean_trades': round(np.mean(time_to_target), 0) if time_to_target else None,
                'median_trades': round(np.median(time_to_target), 0) if time_to_target else None,
                'p25_trades': round(np.percentile(time_to_target, 25), 0) if len(time_to_target) > 4 else None,
                'p75_trades': round(np.percentile(time_to_target, 75), 0) if len(time_to_target) > 4 else None,
            },
            'double_capital': {
                'mean_trades': round(np.mean(time_to_double), 0) if time_to_double else None,
                'median_trades': round(np.median(time_to_double), 0) if time_to_double else None,
            },
        },
        
        'sample_curves': sample_curves,
    }
    
    return results


def kelly_optimization(pnl_distribution: np.ndarray, capital: float, n_sims: int, trades: int):
    """
    Find the optimal risk level by running Monte Carlo at different risk multipliers.
    Kelly Criterion via simulation — more accurate than the formula for fat-tailed distributions.
    """
    risk_levels = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0]
    results = []
    
    for risk in risk_levels:
        mc = run_monte_carlo(pnl_distribution, capital, min(n_sims, 2000), trades, risk)
        
        # Geometric mean growth rate (CAGR-like metric)
        finals = np.array([mc['final_capital']['mean']])
        growth = (mc['final_capital']['median'] / capital) ** (1 / max(trades / 250, 1)) - 1
        
        results.append({
            'risk_pct': round(risk * 1.0, 2),  # Base is 1%
            'median_roi': mc['roi']['median_pct'],
            'p5_roi': mc['roi']['p5_pct'],
            'prob_profit': mc['probabilities']['profit'],
            'prob_ruin': mc['probabilities']['ruin'],
            'prob_70pct': mc['probabilities']['target_70pct_roi'],
            'median_dd': mc['drawdown']['median_max_dd_pct'],
            'p95_dd': mc['drawdown']['p95_max_dd_pct'],
            'geometric_growth': round(growth * 100, 4),
        })
    
    # Optimal = highest geometric growth with ruin probability < 5%
    safe_results = [r for r in results if r['prob_ruin'] < 5.0]
    if safe_results:
        optimal = max(safe_results, key=lambda x: x['geometric_growth'])
    else:
        optimal = min(results, key=lambda x: x['prob_ruin'])
    
    return results, optimal


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_report(
    mc_results: Dict,
    kelly_results: Tuple,
    pnl_stats: Dict,
    capital: float,
    trades_per_month: float,
) -> str:
    """Generate the comprehensive Monte Carlo report."""
    
    r = mc_results
    kelly_all, kelly_optimal = kelly_results
    
    months = r['config']['trades_per_simulation'] / max(trades_per_month, 1)
    
    lines = []
    lines.append("=" * 70)
    lines.append("  MONTE CARLO STRESS TEST — 10,000 SIMULATIONS")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"  Capital: ₹{capital:,.0f} | Risk: {r['config']['effective_risk_pct']}% per trade")
    lines.append(f"  Simulating: {r['config']['trades_per_simulation']} trades (~{months:.0f} months)")
    lines.append("=" * 70)
    
    # --- HEADLINE PROBABILITIES ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  THE BIG QUESTIONS")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  Q: What's the probability I make money?")
    lines.append(f"  A: {r['probabilities']['profit']}%")
    lines.append(f"")
    lines.append(f"  Q: What's the probability I hit 70% ROI (₹{capital*1.7:,.0f})?")
    lines.append(f"  A: {r['probabilities']['target_70pct_roi']}%")
    if r['time_to_milestone']['target_70pct_roi']['median_trades']:
        est_months = r['time_to_milestone']['target_70pct_roi']['median_trades'] / max(trades_per_month, 1)
        lines.append(f"     Estimated time: ~{est_months:.0f} months ({r['time_to_milestone']['target_70pct_roi']['median_trades']:.0f} trades)")
    lines.append(f"")
    lines.append(f"  Q: What's the probability I double my money?")
    lines.append(f"  A: {r['probabilities']['double_capital']}%")
    if r['time_to_milestone']['double_capital']['median_trades']:
        est_months = r['time_to_milestone']['double_capital']['median_trades'] / max(trades_per_month, 1)
        lines.append(f"     Estimated time: ~{est_months:.0f} months ({r['time_to_milestone']['double_capital']['median_trades']:.0f} trades)")
    lines.append(f"")
    lines.append(f"  Q: What's the probability I get ruined (lose 50%+)?”")
    lines.append(f"  A: {r['probabilities']['ruin']}%")
    lines.append(f"")
    lines.append(f"  Q: What's the worst drawdown I should prepare for?")
    lines.append(f"  A: Median max DD: {r['drawdown']['median_max_dd_pct']}%")
    lines.append(f"     95th percentile: {r['drawdown']['p95_max_dd_pct']}% (1-in-20 bad luck)")
    lines.append(f"     99th percentile: {r['drawdown']['p99_max_dd_pct']}% (1-in-100 worst case)")
    lines.append(f"     Absolute worst: {r['drawdown']['worst_dd_pct']}%")
    
    # --- CAPITAL DISTRIBUTION ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  FINAL CAPITAL DISTRIBUTION (After {r['config']['trades_per_simulation']} trades)")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  Starting Capital: ₹{capital:,.0f}")
    lines.append(f"")
    lines.append(f"  {'Percentile':<15} {'Capital':>15} {'ROI':>10}")
    lines.append(f"  {'─'*15} {'─'*15} {'─'*10}")
    
    fc = r['final_capital']
    for label, key in [('Worst Case', 'min'), ('1st %ile', 'p5'), ('5th %ile', 'p10'),
                        ('25th %ile', 'p25'), ('MEDIAN', 'p50'), ('75th %ile', 'p75'),
                        ('90th %ile', 'p90'), ('95th %ile', 'p95'), ('99th %ile', 'p99'),
                        ('Best Case', 'max')]:
        val = fc[key]
        roi = (val - capital) / capital * 100
        marker = " ◄── YOU ARE HERE (median)" if key == 'p50' else ""
        marker = " ◄── TARGET" if key == 'p75' and roi >= 70 else marker
        lines.append(f"  {label:<15} ₹{val:>12,.0f} {roi:>+9.1f}%{marker}")
    
    # --- PROBABILITY TABLE ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  PROBABILITY TABLE")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  {'Scenario':<35} {'Probability':>12}")
    lines.append(f"  {'─'*35} {'─'*12}")
    
    prob_items = [
        (f"Make any profit", r['probabilities']['profit']),
        (f"Gain 50%+ (₹{capital*1.5:,.0f}+)", r['probabilities']['gain_50pct']),
        (f"Hit 70% ROI target (₹{capital*1.7:,.0f}+)", r['probabilities']['target_70pct_roi']),
        (f"Double capital (₹{capital*2:,.0f}+)", r['probabilities']['double_capital']),
        (f"Triple capital (₹{capital*3:,.0f}+)", r['probabilities']['gain_200pct']),
        (f"--- RISK SIDE ---", ""),
        (f"Lose 10%+ (below ₹{capital*0.9:,.0f})", r['probabilities']['lose_10pct']),
        (f"Lose 20%+ (below ₹{capital*0.8:,.0f})", r['probabilities']['lose_20pct']),
        (f"Lose 30%+ (below ₹{capital*0.7:,.0f})", r['probabilities']['lose_30pct']),
        (f"RUIN (lose 50%+)", r['probabilities']['ruin']),
    ]
    for label, prob in prob_items:
        if prob == "":
            lines.append(f"  {label}")
        else:
            lines.append(f"  {label:<35} {prob:>11.2f}%")
    
    # --- KELLY OPTIMIZATION ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  OPTIMAL RISK SIZING (Kelly Criterion via Simulation)")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  {'Risk %':<8} {'Median ROI':>10} {'5th % ROI':>10} {'P(Profit)':>10} {'P(70% ROI)':>11} {'P(Ruin)':>8} {'Med DD':>7}")
    lines.append(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*10} {'─'*11} {'─'*8} {'─'*7}")
    
    for k in kelly_all:
        marker = " ◄ OPTIMAL" if k['risk_pct'] == kelly_optimal['risk_pct'] else ""
        marker = " ◄ CURRENT" if abs(k['risk_pct'] - 1.0) < 0.01 else marker
        lines.append(f"  {k['risk_pct']:>5.2f}%  {k['median_roi']:>+9.1f}% {k['p5_roi']:>+9.1f}% {k['prob_profit']:>9.1f}% {k['prob_70pct']:>10.1f}% {k['prob_ruin']:>7.1f}% {k['median_dd']:>6.1f}%{marker}")
    
    lines.append(f"")
    lines.append(f"  RECOMMENDATION: Use {kelly_optimal['risk_pct']}% risk per trade")
    lines.append(f"    → Median ROI: {kelly_optimal['median_roi']}%")
    lines.append(f"    → P(70% ROI): {kelly_optimal['prob_70pct']}%")
    lines.append(f"    → P(Ruin): {kelly_optimal['prob_ruin']}%")
    lines.append(f"    → Expected max DD: {kelly_optimal['p95_dd']}% (95th percentile)")
    
    # --- DRAWDOWN ANALYSIS ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  DRAWDOWN DEEP DIVE")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  What to expect during trading:")
    lines.append(f"    Average max drawdown: {r['drawdown']['mean_max_dd_pct']}%")
    lines.append(f"    Average DD duration: {r['drawdown']['mean_dd_duration_trades']} trades")
    lines.append(f"    Longest DD streak: {r['drawdown']['max_dd_duration_trades']} trades")
    lines.append(f"")
    lines.append(f"  PREPARE FOR THIS (95th percentile):")
    lines.append(f"    Max drawdown: {r['drawdown']['p95_max_dd_pct']}% = ₹{capital * r['drawdown']['p95_max_dd_pct'] / 100:,.0f}")
    lines.append(f"    This WILL happen eventually. If you can't stomach it, reduce risk.")
    
    # --- SCALING RECOMMENDATION ---
    lines.append(f"\n{'─'*70}")
    lines.append(f"  SCALING ROADMAP")
    lines.append(f"{'─'*70}")
    lines.append(f"")
    lines.append(f"  Phase 1 (Now): Paper trade with 1% risk on ₹{capital:,.0f}")
    lines.append(f"    Duration: 1-2 months | Validate edge monitor stays GREEN")
    lines.append(f"")
    lines.append(f"  Phase 2: Live with 0.5% risk on ₹{capital:,.0f}")
    lines.append(f"    Duration: 1 month | Half risk to build confidence")
    lines.append(f"")
    lines.append(f"  Phase 3: Live with {min(kelly_optimal['risk_pct'], 1.5):.1f}% risk on ₹{capital:,.0f}")
    lines.append(f"    Duration: 3 months | Use Kelly-optimal risk")
    lines.append(f"")
    
    if kelly_optimal['prob_70pct'] > 50:
        target_months = r['time_to_milestone']['target_70pct_roi']['median_trades'] / max(trades_per_month, 1) if r['time_to_milestone']['target_70pct_roi']['median_trades'] else 12
        lines.append(f"  Phase 4: Scale capital after {target_months:.0f} months if profitable")
        lines.append(f"    Target: ₹{capital * 1.7:,.0f} → reinvest profits → compound")
    
    # --- FINAL VERDICT ---
    lines.append(f"\n{'='*70}")
    lines.append(f"  FINAL VERDICT")
    lines.append(f"{'='*70}")
    
    if r['probabilities']['target_70pct_roi'] >= 50:
        lines.append(f"  70% ROI TARGET: ACHIEVABLE ({r['probabilities']['target_70pct_roi']}% probability)")
    elif r['probabilities']['target_70pct_roi'] >= 25:
        lines.append(f"  70% ROI TARGET: POSSIBLE BUT NOT GUARANTEED ({r['probabilities']['target_70pct_roi']}%)")
        lines.append(f"  Consider: Increase risk to {kelly_optimal['risk_pct']}% OR extend timeframe")
    else:
        lines.append(f"  70% ROI TARGET: UNLIKELY AT CURRENT RISK ({r['probabilities']['target_70pct_roi']}%)")
        lines.append(f"  To improve: Use Kelly-optimal {kelly_optimal['risk_pct']}% risk")
        lines.append(f"  Or: Add more profitable strategies to the survivor pool")
    
    if r['probabilities']['ruin'] < 1:
        lines.append(f"  RUIN RISK: NEGLIGIBLE ({r['probabilities']['ruin']}%) — system is safe")
    elif r['probabilities']['ruin'] < 5:
        lines.append(f"  RUIN RISK: LOW ({r['probabilities']['ruin']}%) — acceptable")
    else:
        lines.append(f"  RUIN RISK: ELEVATED ({r['probabilities']['ruin']}%) — reduce risk immediately")
    
    lines.append(f"")
    lines.append(f"  READY TO TRADE: {'YES' if r['probabilities']['profit'] > 60 and r['probabilities']['ruin'] < 5 else 'NEEDS MORE OPTIMIZATION'}")
    lines.append(f"{'='*70}")
    
    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  MONTE CARLO STRESS TEST — 10,000 SIMULATIONS")
    print("=" * 60)
    
    # Parse CLI args
    capital = DEFAULT_CONFIG['capital']
    n_sims = DEFAULT_CONFIG['n_simulations']
    
    for i, arg in enumerate(sys.argv):
        if arg == '--capital' and i + 1 < len(sys.argv):
            capital = float(sys.argv[i + 1])
        if arg == '--sims' and i + 1 < len(sys.argv):
            n_sims = int(sys.argv[i + 1])
    
    # Load data
    print("\nLoading survivor trades...")
    trades_df = load_survivor_trades()
    
    if len(trades_df) < 10:
        print("ERROR: Need at least 10 trades for meaningful simulation.")
        sys.exit(1)
    
    # Extract P&L distribution
    print("\nExtracting P&L distribution...")
    pnl_dist = extract_pnl_distribution(trades_df, capital)
    
    # Estimate trades per month
    if 'entry_time' in trades_df.columns:
        trades_df['entry_dt'] = pd.to_datetime(trades_df['entry_time'])
        date_range = (trades_df['entry_dt'].max() - trades_df['entry_dt'].min()).days
        months = max(date_range / 30, 1)
        trades_per_month = len(trades_df) / months
    else:
        trades_per_month = len(trades_df) / 6  # 6 phases ~18 months
    
    print(f"  Estimated trades per month: {trades_per_month:.1f}")
    
    # Simulate 12 months forward
    trades_forward = int(trades_per_month * 12)
    print(f"  Simulating {trades_forward} trades (~12 months)")
    
    # Run main Monte Carlo
    print(f"\nRunning {n_sims:,} Monte Carlo simulations...")
    mc_results = run_monte_carlo(
        pnl_dist, capital, n_sims, trades_forward,
        risk_multiplier=1.0,
        ruin_threshold_pct=50
    )
    print("  Main simulation complete.")
    
    # Run Kelly optimization
    print("\nRunning Kelly optimization (12 risk levels)...")
    kelly_all, kelly_optimal = kelly_optimization(pnl_dist, capital, n_sims, trades_forward)
    print(f"  Optimal risk: {kelly_optimal['risk_pct']}%")
    
    # Run Monte Carlo at OPTIMAL risk level
    print(f"\nRunning simulation at optimal {kelly_optimal['risk_pct']}% risk...")
    mc_optimal = run_monte_carlo(
        pnl_dist, capital, n_sims, trades_forward,
        risk_multiplier=kelly_optimal['risk_pct'] / 1.0,
        ruin_threshold_pct=50
    )
    
    # Generate report
    print("\nGenerating report...")
    report = generate_report(mc_results, (kelly_all, kelly_optimal), {}, capital, trades_per_month)
    
    # Save report
    report_path = 'pipeline/results/MONTE_CARLO_REPORT.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  Report saved: {report_path}")
    
    # Save raw results
    results_path = 'pipeline/results/monte_carlo_results.json'
    save_data = {
        'config': DEFAULT_CONFIG,
        'at_current_risk': mc_results,
        'at_optimal_risk': mc_optimal,
        'kelly_optimization': kelly_all,
        'kelly_optimal': kelly_optimal,
    }
    # Remove sample curves for JSON (too large)
    save_data['at_current_risk'].pop('sample_curves', None)
    save_data['at_optimal_risk'].pop('sample_curves', None)
    
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"  Raw results saved: {results_path}")
    
    # Also generate report at OPTIMAL risk
    report_optimal = generate_report(mc_optimal, (kelly_all, kelly_optimal), {}, capital, trades_per_month)
    with open('pipeline/results/MONTE_CARLO_REPORT_OPTIMAL_RISK.md', 'w', encoding='utf-8') as f:
        f.write(report_optimal)
    print(f"  Optimal risk report saved: pipeline/results/MONTE_CARLO_REPORT_OPTIMAL_RISK.md")
    
    # Print the main report
    print("\n" + report)
    
    # Print comparison: Current vs Optimal risk
    print(f"\n{'='*70}")
    print(f"  COMPARISON: Current 1% Risk vs Optimal {kelly_optimal['risk_pct']}% Risk")
    print(f"{'='*70}")
    opt_risk_str = f"{kelly_optimal['risk_pct']}% Risk"
    print(f"  {'Metric':<30} {'1% Risk':>15} {opt_risk_str:>15}")
    print(f"  {'─'*30} {'─'*15} {'─'*15}")
    print(f"  {'Median ROI':<30} {mc_results['roi']['median_pct']:>+14.1f}% {mc_optimal['roi']['median_pct']:>+14.1f}%")
    print(f"  {'P(Profit)':<30} {mc_results['probabilities']['profit']:>14.1f}% {mc_optimal['probabilities']['profit']:>14.1f}%")
    print(f"  {'P(70% ROI)':<30} {mc_results['probabilities']['target_70pct_roi']:>14.1f}% {mc_optimal['probabilities']['target_70pct_roi']:>14.1f}%")
    print(f"  {'P(Double)':<30} {mc_results['probabilities']['double_capital']:>14.1f}% {mc_optimal['probabilities']['double_capital']:>14.1f}%")
    print(f"  {'P(Ruin)':<30} {mc_results['probabilities']['ruin']:>14.1f}% {mc_optimal['probabilities']['ruin']:>14.1f}%")
    print(f"  {'95th % Max DD':<30} {mc_results['drawdown']['p95_max_dd_pct']:>13.1f}% {mc_optimal['drawdown']['p95_max_dd_pct']:>13.1f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()