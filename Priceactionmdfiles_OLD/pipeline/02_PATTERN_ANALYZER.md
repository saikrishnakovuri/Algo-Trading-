
Action: file_editor create /app/pipeline/02_PATTERN_ANALYZER.md --file-text "# PHASE 1 → INSIGHT EXTRACTION: Pattern Analyzer
## Mine the raw data for every profitable combination

---

## MISSION

Read `pipeline/results/phase1_raw_results.csv` and extract EVERY insight:
- Which strategies make money?
- Which hours print money?
- Which days win?
- Which TP/SL method is best per strategy?
- Which direction (CE/PE) works better per strategy?
- Which regime (trending/ranging) works for what?
- What confidence thresholds optimize win rate?
- What combinations of the above create 70%+ ROI?

Save the results as `pipeline/results/phase1_insights.json` and `pipeline/results/optimized_config.json`.

---

## IMPLEMENTATION

### Create: `pattern_analyzer.py`

```python
\"\"\"
PATTERN ANALYZER
================
Reads raw backtest results and finds every profitable combination.
Outputs an optimized configuration for the next validation phase.
\"\"\"

import pandas as pd
import numpy as np
import json
from itertools import product


def load_results(csv_path):
    df = pd.read_csv(csv_path)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    print(f\"Loaded {len(df)} trades from {csv_path}\")
    return df


def analyze_dimension(df, group_col, min_trades=10):
    \"\"\"Analyze P&L by a single dimension (strategy, hour, day, etc.)\"\"\"
    results = []
    for val, group in df.groupby(group_col):
        if len(group) < min_trades:
            continue
        wins = group[group['result'] == 'WIN']
        losses = group[group['result'] == 'LOSS']
        gp = wins['pnl'].sum() if len(wins) > 0 else 0
        gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.01
        results.append({
            'value': str(val),
            'trades': len(group),
            'wins': len(wins),
            'win_rate': round(len(wins) / len(group) * 100, 1),
            'total_pnl': round(group['pnl'].sum(), 2),
            'avg_pnl': round(group['pnl'].mean(), 2),
            'profit_factor': round(gp / gl, 2),
            'avg_win': round(wins['pnl'].mean(), 2) if len(wins) > 0 else 0,
            'avg_loss': round(losses['pnl'].mean(), 2) if len(losses) > 0 else 0,
            'best_trade': round(group['pnl'].max(), 2),
            'worst_trade': round(group['pnl'].min(), 2),
        })
    return sorted(results, key=lambda x: x['total_pnl'], reverse=True)


def analyze_combinations(df, min_trades=5):
    \"\"\"
    Find the TOP performing COMBINATIONS of:
    strategy + sl_method + hour + day + direction + regime
    
    This is the core insight extraction.
    \"\"\"
    combos = []
    
    # Strategy + SL Method + Hour + Day
    for (strat, sl, hour, day), group in df.groupby(
        ['strategy_name', 'sl_method', 'hour_of_entry', 'day_of_week']
    ):
        if len(group) < min_trades:
            continue
        wins = group[group['result'] == 'WIN']
        losses = group[group['result'] == 'LOSS']
        gp = wins['pnl'].sum() if len(wins) > 0 else 0
        gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.01
        pf = gp / gl
        wr = len(wins) / len(group) * 100
        
        combos.append({
            'strategy': strat,
            'sl_method': sl,
            'hour': int(hour),
            'day': day,
            'trades': len(group),
            'win_rate': round(wr, 1),
            'pnl': round(group['pnl'].sum(), 2),
            'profit_factor': round(pf, 2),
            'avg_rr': round(group['risk_reward_achieved'].mean(), 2),
        })
    
    # Sort by profit factor (most robust) then by P&L (most profitable)
    combos = sorted(combos, key=lambda x: (x['profit_factor'], x['pnl']), reverse=True)
    return combos


def analyze_by_direction(df, min_trades=10):
    \"\"\"CE vs PE performance per strategy.\"\"\"
    results = []
    for (strat, direction), group in df.groupby(['strategy_name', 'direction']):
        if len(group) < min_trades:
            continue
        wins = group[group['result'] == 'WIN']
        results.append({
            'strategy': strat,
            'direction': direction,
            'trades': len(group),
            'win_rate': round(len(wins) / len(group) * 100, 1),
            'pnl': round(group['pnl'].sum(), 2),
        })
    return sorted(results, key=lambda x: x['pnl'], reverse=True)


def analyze_by_regime(df, min_trades=10):
    \"\"\"Performance per market regime.\"\"\"
    results = []
    for (strat, regime), group in df.groupby(['strategy_name', 'market_regime']):
        if len(group) < min_trades:
            continue
        wins = group[group['result'] == 'WIN']
        gp = wins['pnl'].sum() if len(wins) > 0 else 0
        gl = abs(group[group['result'] == 'LOSS']['pnl'].sum()) or 0.01
        results.append({
            'strategy': strat,
            'regime': regime,
            'trades': len(group),
            'win_rate': round(len(wins) / len(group) * 100, 1),
            'pnl': round(group['pnl'].sum(), 2),
            'profit_factor': round(gp / gl, 2),
        })
    return sorted(results, key=lambda x: x['pnl'], reverse=True)


def find_confidence_threshold(df):
    \"\"\"Find optimal confidence cutoff per strategy.\"\"\"
    thresholds = {}
    for strat, group in df.groupby('strategy_name'):
        best_pf = 0
        best_thresh = 0
        for thresh in np.arange(0.5, 1.0, 0.05):
            filtered = group[group['confidence'] >= thresh]
            if len(filtered) < 5:
                continue
            wins = filtered[filtered['result'] == 'WIN']
            gp = wins['pnl'].sum() if len(wins) > 0 else 0
            gl = abs(filtered[filtered['result'] == 'LOSS']['pnl'].sum()) or 0.01
            pf = gp / gl
            if pf > best_pf:
                best_pf = pf
                best_thresh = thresh
        thresholds[strat] = {
            'optimal_confidence': round(best_thresh, 2),
            'profit_factor_at_threshold': round(best_pf, 2)
        }
    return thresholds


def generate_optimized_config(insights):
    \"\"\"
    From all insights, generate the optimized config for the next phase.
    
    Selection criteria for each dimension:
    - Strategy: PF > 1.3 AND trades > 10
    - Hour: PF > 1.0 AND positive P&L
    - Day: PF > 1.0 AND positive P&L
    - SL Method: Highest PF across all strategies
    - Direction: Best per strategy
    - Regime: Which regimes to trade per strategy
    - Confidence: Optimal per strategy
    \"\"\"
    config = {
        'phase': 2,
        'generated_from': 'phase1_insights',
        'selection_criteria': {
            'min_profit_factor': 1.3,
            'min_trades': 10,
            'min_win_rate': 35.0,
        },
        
        # TOP STRATEGIES (PF > 1.3 with enough trades)
        'strategies': [],
        
        # BEST HOURS
        'allowed_hours': [],
        
        # BEST DAYS
        'allowed_days': [],
        
        # BEST SL METHOD
        'sl_method': None,
        
        # TOP COMBINATIONS (strategy + hour + day + sl)
        'top_combinations': [],
        
        # PER-STRATEGY CONFIGS
        'strategy_configs': {},
    }
    
    # Select top strategies
    for s in insights['by_strategy']:
        if s['profit_factor'] >= 1.3 and s['trades'] >= 10 and s['win_rate'] >= 35:
            config['strategies'].append(s['value'])
    
    # Select profitable hours
    for h in insights['by_hour']:
        if h['profit_factor'] >= 1.0 and h['total_pnl'] > 0:
            config['allowed_hours'].append(int(h['value']))
    
    # Select profitable days
    for d in insights['by_day']:
        if d['profit_factor'] >= 1.0 and d['total_pnl'] > 0:
            config['allowed_days'].append(d['value'])
    
    # Best SL method
    sl_methods = insights['by_sl_method']
    if sl_methods:
        best_sl = max(sl_methods, key=lambda x: x['profit_factor'])
        config['sl_method'] = best_sl['value']
    
    # Top 10 combinations
    config['top_combinations'] = insights['top_combinations'][:10]
    
    # Per-strategy confidence thresholds
    config['strategy_configs'] = insights.get('confidence_thresholds', {})
    
    # Per-strategy direction preference
    for item in insights.get('by_direction', []):
        strat = item['strategy']
        if strat not in config['strategy_configs']:
            config['strategy_configs'][strat] = {}
        if item['pnl'] > 0:
            config['strategy_configs'][strat]['preferred_direction'] = item['direction']
    
    # Per-strategy regime
    for item in insights.get('by_regime', []):
        strat = item['strategy']
        if strat not in config['strategy_configs']:
            config['strategy_configs'][strat] = {}
        if item['profit_factor'] > 1.0:
            if 'allowed_regimes' not in config['strategy_configs'][strat]:
                config['strategy_configs'][strat]['allowed_regimes'] = []
            config['strategy_configs'][strat]['allowed_regimes'].append(item['regime'])
    
    return config


def main():
    print(\"=\" * 60)
    print(\"  PATTERN ANALYZER — Mining Phase 1 Raw Data\")
    print(\"=\" * 60)
    
    df = load_results('pipeline/results/phase1_raw_results.csv')
    
    insights = {}
    
    # Analyze every dimension
    print(\"\nAnalyzing by Strategy...\")
    insights['by_strategy'] = analyze_dimension(df, 'strategy_name')
    
    print(\"Analyzing by Hour...\")
    insights['by_hour'] = analyze_dimension(df, 'hour_of_entry')
    
    print(\"Analyzing by Day...\")
    insights['by_day'] = analyze_dimension(df, 'day_of_week')
    
    print(\"Analyzing by SL Method...\")
    insights['by_sl_method'] = analyze_dimension(df, 'sl_method')
    
    print(\"Analyzing by Month...\")
    insights['by_month'] = analyze_dimension(df, 'month')
    
    print(\"Analyzing by Direction...\")
    insights['by_direction'] = analyze_by_direction(df)
    
    print(\"Analyzing by Regime...\")
    insights['by_regime'] = analyze_by_regime(df)
    
    print(\"Finding optimal confidence thresholds...\")
    insights['confidence_thresholds'] = find_confidence_threshold(df)
    
    print(\"Finding top combinations...\")
    insights['top_combinations'] = analyze_combinations(df)
    
    # Save insights
    with open('pipeline/results/phase1_insights.json', 'w') as f:
        json.dump(insights, f, indent=2, default=str)
    print(f\"\nInsights saved to pipeline/results/phase1_insights.json\")
    
    # Generate optimized config
    config = generate_optimized_config(insights)
    with open('pipeline/results/optimized_config.json', 'w') as f:
        json.dump(config, f, indent=2, default=str)
    print(f\"Optimized config saved to pipeline/results/optimized_config.json\")
    
    # Print summary
    print(f\"\n{'='*60}\")
    print(f\"  TOP 10 STRATEGIES BY PROFIT FACTOR\")
    print(f\"{'='*60}\")
    for s in insights['by_strategy'][:10]:
        print(f\"  {s['value']:>40} | {s['trades']:>3}t | {s['win_rate']:>5.1f}% WR | PF {s['profit_factor']:>5.2f} | P&L ₹{s['total_pnl']:>10,.2f}\")
    
    print(f\"\n  TOP HOURS:\")
    for h in insights['by_hour'][:5]:
        print(f\"  {h['value']:>10}:00 | {h['trades']:>3}t | {h['win_rate']:>5.1f}% WR | PF {h['profit_factor']:>5.2f} | P&L ₹{h['total_pnl']:>10,.2f}\")
    
    print(f\"\n  TOP DAYS:\")
    for d in insights['by_day']:
        print(f\"  {d['value']:>12} | {d['trades']:>3}t | {d['win_rate']:>5.1f}% WR | PF {d['profit_factor']:>5.2f} | P&L ₹{d['total_pnl']:>10,.2f}\")
    
    print(f\"\n  BEST SL METHOD:\")
    for s in insights['by_sl_method'][:3]:
        print(f\"  {s['value']:>20} | {s['trades']:>4}t | PF {s['profit_factor']:>5.2f} | P&L ₹{s['total_pnl']:>10,.2f}\")
    
    print(f\"\n  TOP 5 COMBINATIONS:\")
    for c in insights['top_combinations'][:5]:
        print(f\"  {c['strategy'][:25]:<25} + {c['sl_method']:<18} + {c['day']:<10} + {c['hour']:02d}:00 | PF {c['profit_factor']:>5.2f} | ₹{c['pnl']:>8,.0f}\")
    
    print(f\"\n  SELECTED FOR NEXT PHASE:\")
    print(f\"    Strategies: {config['strategies']}\")
    print(f\"    Hours: {config['allowed_hours']}\")
    print(f\"    Days: {config['allowed_days']}\")
    print(f\"    SL Method: {config['sl_method']}\")


if __name__ == \"__main__\":
    main()
```

---

## RUN THIS AFTER 01_RAW_DISCOVERY.md COMPLETES.

It reads the Phase 1 CSV, mines every pattern, and creates the config for Phase 2.

**The config file (`optimized_config.json`) is what Phase 2 reads to know what to test.**

## GO.
"
Observation: Create successful: /app/pipeline/02_PATTERN_ANALYZER.md