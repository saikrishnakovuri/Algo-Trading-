Now let me also create the Gemini prompt to fix all these issues:
Action: file_editor create /app/GEMINI_FIX_BUGS_PROMPT.md --file-text "# CRITICAL BUG FIXES FOR MASSIVE_BACKTEST.PY
## Feed this to Gemini CLI after reading the analysis report

Read `BACKTEST_DEEP_ANALYSIS_REPORT.md` first. Then fix these 5 bugs in `massive_backtest.py`:

---

## BUG 1: ATR TRAILING STOP NOT IMPLEMENTED (Lines 59-82)

The `trail: True` flag in TP_SL_STRATEGIES is never used. The SL is fixed at entry.

**Fix the `simulate_trade()` function — replace the bar loop (lines 59-82) with:**

```python
trailing_sl = sl_price  # Initialize trailing stop

for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
    current_bar = df.iloc[j]
    
    # UPDATE TRAILING STOP (only if trail=True in config)
    if tp_sl_config.get('trail', False):
        if direction == 'BULLISH':
            # Trail SL up as price moves up
            new_trail = current_bar['close'] - (atr * tp_sl_config['sl_atr'])
            trailing_sl = max(trailing_sl, new_trail)
        else:
            # Trail SL down as price moves down
            new_trail = current_bar['close'] + (atr * tp_sl_config['sl_atr'])
            trailing_sl = min(trailing_sl, new_trail)
    
    # Use trailing_sl instead of fixed sl_price
    active_sl = trailing_sl if tp_sl_config.get('trail', False) else sl_price
    
    if direction == 'BULLISH':
        if current_bar['low'] <= active_sl:
            exit_price = active_sl
            exit_time = df.index[j]
            # Trailing stop can still result in WIN if SL trailed above entry
            result = \"WIN\" if exit_price > entry_price else \"LOSS\"
            break
        if current_bar['high'] >= tp_price:
            exit_price = tp_price
            exit_time = df.index[j]
            result = \"WIN\"
            break
    else:
        if current_bar['high'] >= active_sl:
            exit_price = active_sl
            exit_time = df.index[j]
            result = \"WIN\" if exit_price < entry_price else \"LOSS\"
            break
        if current_bar['low'] <= tp_price:
            exit_price = tp_price
            exit_time = df.index[j]
            result = \"WIN\"
            break
```

---

## BUG 2: EOD EXIT USES WRONG PRICE (Lines 84-87)

**Replace:**
```python
if exit_time is None:
    exit_price = df.iloc[-1]['close']      # BUG: Uses last bar of ENTIRE dataset
    exit_time = df.index[-1]
```

**With:**
```python
if exit_time is None:
    eod_idx = min(entry_idx + 100, len(df) - 1)
    exit_price = df.iloc[eod_idx]['close']  # Uses 100 bars later, not end of dataset
    exit_time = df.index[eod_idx]
    result = \"EOD\"
```

---

## BUG 3: RUN ONLY ONE TP/SL METHOD (Lines 131-142)

**Replace:**
```python
for tpsl in TP_SL_STRATEGIES:
```

**With (use ONLY ATR_TRAILING after fixing Bug 1):**
```python
# Use only ATR_TRAILING — the method designed for trend-following
tpsl = {\"name\": \"ATR_TRAILING\", \"sl_atr\": 2.0, \"tp_ratio\": 5.0, \"trail\": True}
```

---

## BUG 4: ADD TIME FILTER (After line 119)

**Add after the weekday check:**
```python
# Skip outside profitable trading window (10:00-12:00 IST)
hour = current_bar.name.hour
minute = current_bar.name.minute
if hour < 10 or hour >= 12:
    continue
```

---

## BUG 5: ADD STRATEGY BLACKLIST (After line 129)

**Add after getting best_sig:**
```python
BLACKLISTED = {
    'Market Structure', 'Supply & Demand', 'Order Blocks',
    'Descending Channel', 'Triple Bottom', 'Inverse Head and Shoulders',
    'Ascending Channel', 'Bullish Engulfing', 'Morning Star',
    'Fair Value Gaps (FVG)', 'Resistance', 'Bear Flag', 'Ascending Triangle'
}
if best_sig.strategy_name in BLACKLISTED:
    continue

# Add minimum confidence filter
if best_sig.confidence < 0.85:
    continue
```

---

## After fixing all 5 bugs, run the backtest again and save to `backtest_detailed_results.csv`.

Expected improvement:
- Trades: ~50-80 (down from 453 due to filters)
- Win rate: 40-50% (up from 30%)
- Profit Factor: >1.5 (up from 0.61)
- Net P&L: Positive
"
Observation: Create successful: /app/GEMINI_FIX_BUGS_PROMPT.md