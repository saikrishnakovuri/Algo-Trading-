
Action: file_editor create /app/pipeline/01_RAW_DISCOVERY.md --file-text "# PHASE 1: RAW DISCOVERY — Run Everything, Filter Nothing
## Capture the FULL signal landscape across 3 months

---

## MISSION

Run **every strategy** the engine has, on **every bar**, at **every hour**, on **every day**, with **multiple TP/SL configs** — and save EVERYTHING.

No filters. No blacklists. No time gates. No confidence floors. We want the RAW truth.

This data becomes the goldmine we mine for patterns.

---

## CONFIGURATION

```python
PHASE1_CONFIG = {
    'phase': 1,
    'period': {
        'start': '2024-10-01',
        'end': '2024-12-31',
    },
    'capital': 500000,
    'risk_pct': 0.01,
    
    # NO FILTERS — run everything
    'excluded_days': [],           # Trade ALL days
    'trading_hours': (9, 16),      # Full market hours 9:15-15:30
    'min_confidence': 0.0,         # Accept ALL signals
    'strategy_blacklist': [],      # ALL strategies active
    'require_trending': False,     # No regime filter
    
    # Test MULTIPLE TP/SL methods per signal
    'tp_sl_configs': [
        {'name': 'TRAIL_2ATR_NOTP', 'sl_atr': 2.0, 'tp_ratio': None, 'trail': True},
        {'name': 'TRAIL_1.5ATR_NOTP', 'sl_atr': 1.5, 'tp_ratio': None, 'trail': True},
        {'name': 'TRAIL_2.5ATR_NOTP', 'sl_atr': 2.5, 'tp_ratio': None, 'trail': True},
        {'name': 'FIXED_2R', 'sl_atr': 1.5, 'tp_ratio': 2.0, 'trail': False},
        {'name': 'FIXED_3R', 'sl_atr': 1.5, 'tp_ratio': 3.0, 'trail': False},
        {'name': 'FIXED_5R', 'sl_atr': 2.0, 'tp_ratio': 5.0, 'trail': False},
    ],
    
    # Scan every bar (not every 3rd)
    'scan_interval': 1,
    
    # Extended lookahead for trailing
    'lookahead_bars': 200,
    
    # Output
    'output_csv': 'pipeline/results/phase1_raw_results.csv',
}
```

---

## IMPLEMENTATION

### Step 1: Load ALL Data

```python
def load_data(config):
    df = pd.read_csv(DATA_FILE)
    df.index = pd.to_datetime(df['Datetime'])
    df.columns = [c.lower() for c in df.columns]
    
    # Filter to phase period
    start = pd.Timestamp(config['period']['start'])
    end = pd.Timestamp(config['period']['end'])
    df = df[(df.index >= start) & (df.index <= end)]
    
    print(f\"Phase {config['phase']}: Loaded {len(df)} bars ({start.date()} to {end.date()})\")
    return df
```

### Step 2: Run Every Strategy on Every Bar

```python
def run_raw_discovery(config):
    engine = UnifiedStrategyEngine()
    df = load_data(config)
    
    all_trades = []
    trade_id = 0
    
    for i in range(50, len(df), config['scan_interval']):
        if i % 500 == 0:
            print(f\"  Scanning bar {i}/{len(df)}...\")
        
        current_bar = df.iloc[i]
        current_window = df.iloc[:i+1]
        
        # Get ALL signals (no filtering)
        signals = engine.get_signals(current_window, backtest_mode=True)
        if not signals:
            continue
        
        # Process EVERY signal (not just the best one)
        for sig in signals:
            # Skip if confidence is literally 0
            if sig.confidence <= 0:
                continue
            
            direction = 'BULLISH' if sig.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else 'BEARISH'
            
            # Detect market regime at this point
            regime = detect_regime(current_window)
            
            # Test EVERY TP/SL config on this signal
            for tpsl in config['tp_sl_configs']:
                trade_id += 1
                result = simulate_trade(df, i, direction, tpsl, config['lookahead_bars'])
                
                if result is None:
                    continue
                
                result.update({
                    'trade_id': trade_id,
                    'phase': config['phase'],
                    'strategy_name': sig.strategy_name,
                    'signal_type': sig.signal_type.value,
                    'confidence': sig.confidence,
                    'direction': 'CE' if direction == 'BULLISH' else 'PE',
                    'sl_method': tpsl['name'],
                    'sl_atr_multiplier': tpsl['sl_atr'],
                    'day_of_week': current_bar.name.strftime('%A'),
                    'hour_of_entry': current_bar.name.hour,
                    'minute_of_entry': current_bar.name.minute,
                    'market_regime': regime,
                    'month': current_bar.name.strftime('%B'),
                    'week_number': current_bar.name.isocalendar()[1],
                })
                all_trades.append(result)
    
    # Save everything
    results_df = pd.DataFrame(all_trades)
    results_df.to_csv(config['output_csv'], index=False)
    print(f\"\nPhase 1 complete: {len(results_df)} trades saved to {config['output_csv']}\")
    print(f\"Unique strategies: {results_df['strategy_name'].nunique()}\")
    print(f\"Unique TP/SL methods: {results_df['sl_method'].nunique()}\")
    
    return results_df
```

### Step 3: Enhanced Simulate Trade (with full tracking)

```python
def simulate_trade(df, entry_idx, direction, tp_sl_config, lookahead=200):
    \"\"\"Simulate trade and return ALL details for analysis.\"\"\"
    entry_bar = df.iloc[entry_idx]
    entry_price = entry_bar['close']
    
    if entry_idx < 14:
        return None
    
    atr = (df['high'] - df['low']).iloc[entry_idx-14:entry_idx].mean()
    if atr == 0:
        return None
    
    sl_dist = atr * tp_sl_config['sl_atr']
    risk_amt = 500000 * 0.01  # 1% of capital
    position_size = risk_amt / sl_dist if sl_dist > 0 else 0
    
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
    exit_reason = \"UNKNOWN\"
    
    is_trailing = tp_sl_config.get('trail', False)
    
    for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(df))):
        bar = df.iloc[j]
        
        # Update trailing stop
        if is_trailing:
            if direction == 'BULLISH':
                new_trail = bar['close'] - (atr * tp_sl_config['sl_atr'])
                trailing_sl = max(trailing_sl, new_trail)
            else:
                new_trail = bar['close'] + (atr * tp_sl_config['sl_atr'])
                trailing_sl = min(trailing_sl, new_trail)
        
        active_sl = trailing_sl if is_trailing else sl_price
        
        if direction == 'BULLISH':
            if bar['low'] <= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                exit_reason = 'TRAIL_HIT' if is_trailing and active_sl > sl_price else 'SL_HIT'
                result = \"WIN\" if exit_price > entry_price else \"LOSS\"
                break
            if tp_price and bar['high'] >= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = \"WIN\"
                exit_reason = 'TP_HIT'
                break
        else:
            if bar['high'] >= active_sl:
                exit_price = active_sl
                exit_time = df.index[j]
                exit_reason = 'TRAIL_HIT' if is_trailing and active_sl < sl_price else 'SL_HIT'
                result = \"WIN\" if exit_price < entry_price else \"LOSS\"
                break
            if tp_price and bar['low'] <= tp_price:
                exit_price = tp_price
                exit_time = df.index[j]
                result = \"WIN\"
                exit_reason = 'TP_HIT'
                break
    
    if exit_time is None:
        eod_idx = min(entry_idx + lookahead, len(df) - 1)
        exit_price = df.iloc[eod_idx]['close']
        exit_time = df.index[eod_idx]
        result = \"EOD\"
        exit_reason = \"EOD\"
    
    price_change = (exit_price - entry_price) if direction == 'BULLISH' else (entry_price - exit_price)
    pnl = price_change * position_size
    duration = (exit_time - df.index[entry_idx]).total_seconds() / 60
    rr_achieved = price_change / sl_dist if sl_dist > 0 else 0
    
    return {
        'entry_time': df.index[entry_idx],
        'exit_time': exit_time,
        'entry_price': round(entry_price, 2),
        'exit_price': round(exit_price, 2),
        'stop_loss': round(sl_price, 2),
        'take_profit': round(tp_price, 2) if tp_price else None,
        'atr_at_entry': round(atr, 2),
        'position_size': round(position_size, 4),
        'pnl': round(pnl, 2),
        'pnl_pct': round((pnl / 500000) * 100, 4),
        'result': result,
        'exit_reason': exit_reason,
        'holding_period_minutes': round(duration, 0),
        'risk_reward_achieved': round(rr_achieved, 2),
    }


def detect_regime(df, lookback=50):
    \"\"\"Classify current market as trending or ranging.\"\"\"
    recent = df.iloc[-lookback:]
    ma20 = recent['close'].rolling(20).mean()
    
    if len(ma20.dropna()) < 5:
        return 'UNKNOWN'
    
    slope = (ma20.iloc[-1] - ma20.iloc[-10]) / ma20.iloc[-10] * 100
    
    if slope > 0.15:
        return 'TRENDING_UP'
    elif slope < -0.15:
        return 'TRENDING_DOWN'
    else:
        return 'RANGING'
```

### Step 4: Run and Print Summary

```python
if __name__ == \"__main__\":
    results = run_raw_discovery(PHASE1_CONFIG)
    
    print(f\"\n{'='*60}\")
    print(f\"  PHASE 1 RAW DISCOVERY — SUMMARY\")
    print(f\"{'='*60}\")
    print(f\"  Total trades: {len(results)}\")
    print(f\"  Net P&L: ₹{results['pnl'].sum():,.2f}\")
    print(f\"  Win Rate: {(results['result']=='WIN').mean()*100:.1f}%\")
    print(f\"  Unique strategies: {results['strategy_name'].nunique()}\")
    print(f\"  Unique hours: {sorted(results['hour_of_entry'].unique())}\")
    print(f\"  Unique days: {sorted(results['day_of_week'].unique())}\")
    print(f\"  Data saved to: {PHASE1_CONFIG['output_csv']}\")
```

---

## EXPECTED OUTPUT

A massive CSV with potentially thousands of trades covering every combination of:
- 48 strategies × 6 TP/SL methods × 5 days × 7 hours × 3 months

This is the raw truth. No opinions. No filters. Just data.

**The next step (02_PATTERN_ANALYZER.md) will mine this data for gold.**

## RUN THIS FIRST. SAVE EVERYTHING. DO NOT FILTER ANYTHING. GO.
"
Observation: Create successful: /app/pipeline/01_RAW_DISCOVERY.md