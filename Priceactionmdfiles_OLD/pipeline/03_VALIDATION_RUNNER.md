
Action: file_editor create /app/pipeline/03_VALIDATION_RUNNER.md --file-text "# VALIDATION RUNNER — Phases 2 through 6
## Test the survivors on NEW data, kill what fails, keep what lives

---

## MISSION

This file runs ONE validation phase at a time. Each run:
1. Reads `optimized_config.json` (created by previous phase)
2. Runs ONLY the approved strategies/hours/days/SL on NEW 3-month data
3. Saves results to `phaseN_results.csv`
4. Analyzes results — kills anything that lost money
5. Updates `optimized_config.json` for the NEXT phase

**Run this file 5 times (Phases 2-6). It auto-detects which phase to run.**

---

## DATA PERIODS

```python
PHASE_PERIODS = {
    2: {'start': '2025-01-01', 'end': '2025-03-31'},
    3: {'start': '2025-04-01', 'end': '2025-06-30'},
    4: {'start': '2025-07-01', 'end': '2025-09-30'},
    5: {'start': '2025-10-01', 'end': '2025-12-31'},
    6: {'start': '2026-01-01', 'end': '2026-03-31'},
}
```

Adjust if your data doesn't cover these periods. Use whatever 3-month windows you have.

---

## IMPLEMENTATION

### Create: `validation_runner.py`

```python
\"\"\"
VALIDATION RUNNER
=================
Reads optimized_config.json, runs validation on new data period,
analyzes results, removes losers, saves updated config.

Auto-detects current phase from config file.
\"\"\"

import pandas as pd
import numpy as np
import json
import os
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType


PHASE_PERIODS = {
    2: {'start': '2025-01-01', 'end': '2025-03-31'},
    3: {'start': '2025-04-01', 'end': '2025-06-30'},
    4: {'start': '2025-07-01', 'end': '2025-09-30'},
    5: {'start': '2025-10-01', 'end': '2025-12-31'},
    6: {'start': '2026-01-01', 'end': '2026-03-31'},
}

DATA_FILE = \"../data/nifty50_5m.csv\"
CAPITAL = 500000


def load_config():
    with open('pipeline/results/optimized_config.json', 'r') as f:
        return json.load(f)


def save_config(config):
    # Save backup of previous config
    phase = config['phase']
    backup_path = f'pipeline/results/config_phase{phase-1}_backup.json'
    if os.path.exists('pipeline/results/optimized_config.json'):
        os.rename('pipeline/results/optimized_config.json', backup_path)
    
    with open('pipeline/results/optimized_config.json', 'w') as f:
        json.dump(config, f, indent=2, default=str)


def run_validation(config):
    phase = config['phase']
    period = PHASE_PERIODS[phase]
    
    print(f\"\n{'='*60}\")
    print(f\"  PHASE {phase} VALIDATION\")
    print(f\"  Period: {period['start']} to {period['end']}\")
    print(f\"  Strategies: {config['strategies']}\")
    print(f\"  Hours: {config['allowed_hours']}\")
    print(f\"  Days: {config['allowed_days']}\")
    print(f\"  SL Method: {config['sl_method']}\")
    print(f\"{'='*60}\")
    
    engine = UnifiedStrategyEngine()
    
    # Load data for this period
    df = pd.read_csv(DATA_FILE)
    df.index = pd.to_datetime(df['Datetime'])
    df.columns = [c.lower() for c in df.columns]
    start = pd.Timestamp(period['start'])
    end = pd.Timestamp(period['end'])
    df = df[(df.index >= start) & (df.index <= end)]
    
    if len(df) == 0:
        print(f\"ERROR: No data for period {period['start']} to {period['end']}\")
        print(\"Adjust PHASE_PERIODS to match your available data.\")
        return None
    
    print(f\"Data loaded: {len(df)} bars\")
    
    # Determine SL config
    SL_CONFIGS = {
        'TRAIL_2ATR_NOTP': {'sl_atr': 2.0, 'tp_ratio': None, 'trail': True},
        'TRAIL_1.5ATR_NOTP': {'sl_atr': 1.5, 'tp_ratio': None, 'trail': True},
        'TRAIL_2.5ATR_NOTP': {'sl_atr': 2.5, 'tp_ratio': None, 'trail': True},
        'FIXED_2R': {'sl_atr': 1.5, 'tp_ratio': 2.0, 'trail': False},
        'FIXED_3R': {'sl_atr': 1.5, 'tp_ratio': 3.0, 'trail': False},
        'FIXED_5R': {'sl_atr': 2.0, 'tp_ratio': 5.0, 'trail': False},
    }
    tpsl = SL_CONFIGS.get(config['sl_method'], SL_CONFIGS['TRAIL_2ATR_NOTP'])
    tpsl['name'] = config['sl_method']
    
    trades = []
    trade_id = 0
    
    allowed_days_set = set(config['allowed_days'])
    allowed_hours_set = set(config['allowed_hours'])
    allowed_strategies = set(config['strategies'])
    
    for i in range(50, len(df)):
        current_bar = df.iloc[i]
        
        # Day filter
        day_name = current_bar.name.strftime('%A')
        if day_name not in allowed_days_set:
            continue
        
        # Hour filter
        hour = current_bar.name.hour
        if hour not in allowed_hours_set:
            continue
        
        current_window = df.iloc[:i+1]
        signals = engine.get_signals(current_window, backtest_mode=True)
        
        if not signals:
            continue
        
        for sig in signals:
            # Strategy filter
            if sig.strategy_name not in allowed_strategies:
                continue
            
            # Confidence filter (per-strategy)
            strat_config = config.get('strategy_configs', {}).get(sig.strategy_name, {})
            min_conf = strat_config.get('optimal_confidence', 0.70)
            if sig.confidence < min_conf:
                continue
            
            # Direction filter (if set)
            direction = 'BULLISH' if sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
            direction_label = 'CE' if direction == 'BULLISH' else 'PE'
            preferred_dir = strat_config.get('preferred_direction')
            if preferred_dir and direction_label != preferred_dir:
                continue
            
            # Regime filter (if set)
            regime = detect_regime(current_window)
            allowed_regimes = strat_config.get('allowed_regimes')
            if allowed_regimes and regime not in allowed_regimes:
                continue
            
            trade_id += 1
            result = simulate_trade(df, i, direction, tpsl, lookahead=200)
            
            if result is None:
                continue
            
            result.update({
                'trade_id': trade_id,
                'phase': phase,
                'strategy_name': sig.strategy_name,
                'confidence': sig.confidence,
                'direction': direction_label,
                'sl_method': tpsl['name'],
                'day_of_week': day_name,
                'hour_of_entry': hour,
                'market_regime': regime,
                'month': current_bar.name.strftime('%B'),
            })
            trades.append(result)
    
    results_df = pd.DataFrame(trades)
    output_path = f'pipeline/results/phase{phase}_results.csv'
    results_df.to_csv(output_path, index=False)
    
    print(f\"\nPhase {phase} results: {len(results_df)} trades saved to {output_path}\")
    return results_df


def analyze_and_update_config(results_df, config):
    \"\"\"Remove losers, keep winners, update config for next phase.\"\"\"
    phase = config['phase']
    
    if results_df is None or len(results_df) == 0:
        print(\"No results to analyze. Config unchanged.\")
        config['phase'] = phase + 1
        save_config(config)
        return
    
    wins = results_df[results_df['result'] == 'WIN']
    losses = results_df[results_df['result'] == 'LOSS']
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.01
    
    print(f\"\n{'='*60}\")
    print(f\"  PHASE {phase} RESULTS\")
    print(f\"{'='*60}\")
    print(f\"  Total trades: {len(results_df)}\")
    print(f\"  Win Rate: {len(wins)/len(results_df)*100:.1f}%\")
    print(f\"  Profit Factor: {gp/gl:.2f}\")
    print(f\"  Net P&L: ₹{results_df['pnl'].sum():,.2f}\")
    print(f\"  ROI: {results_df['pnl'].sum()/CAPITAL*100:.1f}%\")
    
    # Analyze per strategy in this phase
    surviving_strategies = []
    print(f\"\n  Per-Strategy Performance (Phase {phase}):\")
    for strat, group in results_df.groupby('strategy_name'):
        s_wins = group[group['result'] == 'WIN']
        s_gp = s_wins['pnl'].sum() if len(s_wins) > 0 else 0
        s_gl = abs(group[group['result'] == 'LOSS']['pnl'].sum()) or 0.01
        s_pf = s_gp / s_gl
        s_pnl = group['pnl'].sum()
        s_wr = len(s_wins) / len(group) * 100
        
        status = \"KEEP\" if s_pf >= 1.0 and s_pnl > 0 else \"KILL\"
        print(f\"    {strat:<35} | {len(group):>3}t | {s_wr:>5.1f}% | PF {s_pf:>5.2f} | ₹{s_pnl:>10,.2f} | {status}\")
        
        if status == \"KEEP\":
            surviving_strategies.append(strat)
    
    # Per hour
    surviving_hours = []
    print(f\"\n  Per-Hour Performance:\")
    for hour, group in results_df.groupby('hour_of_entry'):
        h_pnl = group['pnl'].sum()
        status = \"KEEP\" if h_pnl > 0 else \"KILL\"
        print(f\"    {hour:02d}:00 | {len(group):>3}t | P&L: ₹{h_pnl:>10,.2f} | {status}\")
        if status == \"KEEP\":
            surviving_hours.append(int(hour))
    
    # Per day
    surviving_days = []
    print(f\"\n  Per-Day Performance:\")
    for day, group in results_df.groupby('day_of_week'):
        d_pnl = group['pnl'].sum()
        status = \"KEEP\" if d_pnl > 0 else \"KILL\"
        print(f\"    {day:<12} | {len(group):>3}t | P&L: ₹{d_pnl:>10,.2f} | {status}\")
        if status == \"KEEP\":
            surviving_days.append(day)
    
    # Update config for next phase
    if surviving_strategies:
        config['strategies'] = surviving_strategies
    if surviving_hours:
        config['allowed_hours'] = surviving_hours
    if surviving_days:
        config['allowed_days'] = surviving_days
    
    config['phase'] = phase + 1
    
    # Store phase results summary
    if 'phase_history' not in config:
        config['phase_history'] = []
    config['phase_history'].append({
        'phase': phase,
        'trades': len(results_df),
        'win_rate': round(len(wins) / len(results_df) * 100, 1),
        'profit_factor': round(gp / gl, 2),
        'pnl': round(results_df['pnl'].sum(), 2),
        'roi_pct': round(results_df['pnl'].sum() / CAPITAL * 100, 2),
        'surviving_strategies': surviving_strategies,
        'surviving_hours': surviving_hours,
        'surviving_days': surviving_days,
    })
    
    save_config(config)
    
    print(f\"\n  SURVIVORS for Phase {phase+1}:\")
    print(f\"    Strategies: {config['strategies']}\")
    print(f\"    Hours: {config['allowed_hours']}\")
    print(f\"    Days: {config['allowed_days']}\")
    print(f\"\n  Config updated. Run this file again for Phase {phase+1}.\")


# --- Reuse simulate_trade and detect_regime from 01_RAW_DISCOVERY ---
# (Copy those functions here or import from a shared module)

def detect_regime(df, lookback=50):
    recent = df.iloc[-lookback:]
    ma20 = recent['close'].rolling(20).mean()
    if len(ma20.dropna()) < 5:
        return 'UNKNOWN'
    slope = (ma20.iloc[-1] - ma20.iloc[-10]) / ma20.iloc[-10] * 100
    if slope > 0.15: return 'TRENDING_UP'
    elif slope < -0.15: return 'TRENDING_DOWN'
    else: return 'RANGING'


def simulate_trade(df, entry_idx, direction, tp_sl_config, lookahead=200):
    entry_price = df.iloc[entry_idx]['close']
    if entry_idx < 14: return None
    atr = (df['high'] - df['low']).iloc[entry_idx-14:entry_idx].mean()
    if atr == 0: return None
    
    sl_dist = atr * tp_sl_config['sl_atr']
    position_size = (CAPITAL * 0.01) / sl_dist if sl_dist > 0 else 0
    
    if direction == 'BULLISH':
        sl_price = entry_price - sl_dist
        tp_price = entry_price + (sl_dist * tp_sl_config['tp_ratio']) if tp_sl_config.get('tp_ratio') else None
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - (sl_dist * tp_sl_config['tp_ratio']) if tp_sl_config.get('tp_ratio') else None
    
    trailing_sl = sl_price
    exit_price = entry_price
    exit_time = None
    result = \"LOSS\"
    is_trailing = tp_sl_config.get('trail', False)
    
    for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(df))):
        bar = df.iloc[j]
        if is_trailing:
            if direction == 'BULLISH':
                trailing_sl = max(trailing_sl, bar['close'] - atr * tp_sl_config['sl_atr'])
            else:
                trailing_sl = min(trailing_sl, bar['close'] + atr * tp_sl_config['sl_atr'])
        
        active_sl = trailing_sl if is_trailing else sl_price
        
        if direction == 'BULLISH':
            if bar['low'] <= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                result = \"WIN\" if exit_price > entry_price else \"LOSS\"
                break
            if tp_price and bar['high'] >= tp_price:
                exit_price = tp_price; exit_time = df.index[j]; result = \"WIN\"; break
        else:
            if bar['high'] >= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                result = \"WIN\" if exit_price < entry_price else \"LOSS\"
                break
            if tp_price and bar['low'] <= tp_price:
                exit_price = tp_price; exit_time = df.index[j]; result = \"WIN\"; break
    
    if exit_time is None:
        eod_idx = min(entry_idx + lookahead, len(df) - 1)
        exit_price = df.iloc[eod_idx]['close']
        exit_time = df.index[eod_idx]
        result = \"EOD\"
    
    price_change = (exit_price - entry_price) if direction == 'BULLISH' else (entry_price - exit_price)
    pnl = price_change * position_size
    duration = (exit_time - df.index[entry_idx]).total_seconds() / 60
    
    return {
        'entry_time': df.index[entry_idx],
        'exit_time': exit_time,
        'entry_price': round(entry_price, 2),
        'exit_price': round(exit_price, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round((pnl / CAPITAL) * 100, 4),
        'result': result,
        'risk_reward_achieved': round(price_change / sl_dist, 2) if sl_dist > 0 else 0,
        'holding_period_minutes': round(duration, 0),
    }


if __name__ == \"__main__\":
    config = load_config()
    phase = config['phase']
    
    if phase > 6:
        print(\"All 6 phases complete. Run 04_FINAL_SURVIVOR_ENGINE.md next.\")
    else:
        results = run_validation(config)
        analyze_and_update_config(results, config)
```

---

## HOW TO USE

Run this file REPEATEDLY. It auto-increments the phase:

```bash
# First run → Phase 2 (reads Phase 1 config, tests on Jan-Mar 2025)
python validation_runner.py

# Second run → Phase 3 (reads updated config, tests on Apr-Jun 2025)
python validation_runner.py

# ... repeat until Phase 6 ...
python validation_runner.py
```

Each run:
- Tests survivors on new data
- Kills anything that lost money
- Updates config for next run
- Logs history of what survived each phase

## AFTER PHASE 6 → Run 04_FINAL_SURVIVOR_ENGINE.md
"
Observation: Create successful: /app/pipeline/03_VALIDATION_RUNNER.md