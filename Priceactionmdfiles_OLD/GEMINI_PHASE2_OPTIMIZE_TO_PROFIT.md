Great progress — the structural fixes work. **₹2,52,586 improvement** proves the bugs were real. Now the system is clean but too conservative (31 trades, zero in Jan/May). Let me write the Phase 2 prompt to push it to profitability.
Action: file_editor create /app/GEMINI_PHASE2_OPTIMIZE_TO_PROFIT.md --file-text "# PHASE 2: FROM BREAKEVEN TO PROFITABLE
## Systematic Optimization of the Fixed Backtest Engine

Read `BACKTEST_DEEP_ANALYSIS_REPORT.md` for context. The Phase 1 bug fixes are done and working. The system went from -₹2.79L to -₹26.8K. Now we need to cross the profitability line.

---

## CURRENT STATE (After Bug Fixes)

```
P&L:           -₹26,814 (-5.36%)
Total Trades:  31
Months Active: Only Feb & Apr (Jan and May had ZERO trades)
Max Drawdown:  5.3% (excellent risk control)
Problem:       Too few trades. Filters killed everything.
```

The system is OVER-FILTERED. We need to **carefully widen the net** without letting the old garbage back in.

---

## STRATEGY: Controlled Expansion in 4 Steps

### STEP 1: WIDEN THE TRADING WINDOW (Highest Impact)

The 10:00-12:00 window is too narrow. Based on the original data:
- 10:00-11:00 was profitable (+₹42,514)
- 11:00-12:00 was marginal (-₹15,866 but 39.3% win rate — best of any hour)
- 9:45-10:00 catches the post-opening-noise setup entries

**Change trading window from `10:00-12:00` to `09:50-12:30`**

This adds ~25% more candles to scan. The 9:50 start catches setups forming at the end of opening noise. The 12:30 end captures late-morning breakouts that complete in early afternoon.

```python
# In the backtest loop, change the time filter to:
hour = current_bar.name.hour
minute = current_bar.name.minute
time_in_minutes = hour * 60 + minute
if time_in_minutes < 590 or time_in_minutes > 750:  # 9:50 AM to 12:30 PM
    continue
```

**Do NOT go past 12:30.** The original data shows 12:00-15:00 was catastrophic.

---

### STEP 2: LOWER CONFIDENCE THRESHOLD TO 0.80 (WITH CONDITIONS)

The 0.85 floor killed too many signals. But 0.80 had a 29% win rate in the original run — not great.

**Solution: Tiered confidence with strategy-specific minimums.**

```python
# Strategy-specific confidence floors
STRATEGY_MIN_CONFIDENCE = {
    # High-confidence strategies (proven profitable) — can trade at 0.80
    'Lower High & Lower Low': 0.80,
    'Retest Entry': 0.80,
    'Higher High & Higher Low': 0.80,
    
    # Medium-confidence strategies — need 0.85
    'Breakout-Retest-Continuation': 0.85,
    'Head and Shoulders': 0.85,
    'Change of Character (CHOCH)': 0.85,
    'Double Bottom': 0.85,
    
    # Re-enabled with HIGH bar (were borderline) — need 0.90
    'Double Top': 0.90,
    'Triple Top': 0.90,
    'Cup and Handle': 0.90,
    'Falling Wedge': 0.85,
}

# In the backtest loop:
min_conf = STRATEGY_MIN_CONFIDENCE.get(best_sig.strategy_name, 0.85)
if best_sig.confidence < min_conf:
    continue
```

This re-enables 3 more strategies (Double Top, Triple Top, Cup and Handle) but only when they're extremely confident.

---

### STEP 3: OPTIMIZE THE ATR TRAILING MULTIPLIER

The current config is `sl_atr: 2.0, tp_ratio: 5.0`. This means:
- Initial SL = 2x ATR away from entry
- TP target = 10x ATR away (5.0 * 2.0 ATR)
- That's a 1:5 risk-reward which requires very strong trends

**Run a parameter sweep to find the sweet spot:**

```python
# Test these ATR combinations
ATR_CONFIGS = [
    {\"sl_atr\": 1.0, \"tp_ratio\": 3.0, \"trail\": True, \"name\": \"TIGHT_3R\"},
    {\"sl_atr\": 1.5, \"tp_ratio\": 3.0, \"trail\": True, \"name\": \"MED_3R\"},
    {\"sl_atr\": 1.5, \"tp_ratio\": 4.0, \"trail\": True, \"name\": \"MED_4R\"},
    {\"sl_atr\": 2.0, \"tp_ratio\": 3.0, \"trail\": True, \"name\": \"WIDE_3R\"},
    {\"sl_atr\": 2.0, \"tp_ratio\": 4.0, \"trail\": True, \"name\": \"WIDE_4R\"},
    {\"sl_atr\": 2.0, \"tp_ratio\": 5.0, \"trail\": True, \"name\": \"WIDE_5R\"},  # Current
    {\"sl_atr\": 2.5, \"tp_ratio\": 3.0, \"trail\": True, \"name\": \"XWIDE_3R\"},
]

# Run backtest for each config and compare:
for config in ATR_CONFIGS:
    result = run_backtest_with_config(config)
    print(f\"{config['name']:>12} | Trades: {result['trades']:>3} | \"
          f\"WR: {result['win_rate']:>5.1f}% | PF: {result['pf']:.2f} | \"
          f\"P&L: ₹{result['pnl']:>10,.2f}\")

# Pick the config with: PF > 1.5 AND trades > 30 AND win_rate > 35%
```

**My hypothesis:** `sl_atr: 1.5, tp_ratio: 3.0` will perform best because:
- Tighter SL (1.5x ATR) means smaller losses when wrong
- 3R target is achievable within the 10:00-12:30 window (150 min of 5m candles = 30 bars)
- Trail still lets big winners run past 3R

---

### STEP 4: ADD SIMPLE REGIME DETECTION

Instead of blindly trading every signal, add a basic regime filter that checks market direction before entering.

```python
def get_market_regime(df, lookback=50):
    \"\"\"
    Simple regime detection using moving averages and recent highs/lows.
    Returns: 'uptrend', 'downtrend', or 'ranging'
    \"\"\"
    recent = df.iloc[-lookback:]
    
    # Short MA vs Long MA
    ma_short = recent['close'].rolling(10).mean().iloc[-1]
    ma_long = recent['close'].rolling(30).mean().iloc[-1]
    
    # Recent higher highs / lower lows
    highs = recent['high'].rolling(10).max()
    lows = recent['low'].rolling(10).min()
    
    recent_high_trend = highs.iloc[-1] > highs.iloc[-20]  # Making new highs
    recent_low_trend = lows.iloc[-1] < lows.iloc[-20]      # Making new lows
    
    if ma_short > ma_long and recent_high_trend:
        return 'uptrend'
    elif ma_short < ma_long and recent_low_trend:
        return 'downtrend'
    else:
        return 'ranging'
```

**Use regime to filter signals:**

```python
regime = get_market_regime(current_window)

# Only take BUY signals in uptrend, SELL in downtrend
if direction == 'BULLISH' and regime == 'downtrend':
    continue  # Don't buy against the trend
if direction == 'BEARISH' and regime == 'uptrend':
    continue  # Don't sell against the trend

# In ranging market, only take reversal strategies
if regime == 'ranging':
    RANGE_STRATEGIES = {'Retest Entry', 'Double Bottom', 'Double Top', 'Support', 'Resistance'}
    if best_sig.strategy_name not in RANGE_STRATEGIES:
        continue
```

---

## EXECUTION PLAN

```
Step 1: Widen window to 9:50-12:30
  → Run backtest → Record: trades, PF, PnL
  → Expected: +30-50% more trades, slight PF improvement

Step 2: Apply tiered confidence
  → Run backtest → Compare to Step 1
  → Expected: +20% more trades from re-enabled strategies

Step 3: ATR parameter sweep (7 configs)
  → Run all 7 → Pick best by PF + trade count
  → Expected: Find optimal RR that balances wins and trade frequency

Step 4: Add regime filter
  → Run backtest with best ATR config + regime
  → Expected: Win rate jumps to 40%+ by avoiding counter-trend trades

Final: Combine all 4 optimizations → Run comprehensive 3-month backtest
  → Target: PF > 1.5, Win Rate > 40%, Trades > 50, Max DD < 15%
```

---

## IMPLEMENTATION ORDER

Implement and test ONE step at a time. After each step:
1. Run the backtest
2. Print the summary (trades, win rate, PF, P&L, max DD)
3. Compare to previous step
4. If it got WORSE, revert that change and try alternative
5. If it got BETTER, keep it and move to next step

**Create a results comparison table:**

```
==============================================================
  OPTIMIZATION RESULTS TRACKER
==============================================================

Baseline (Phase 1 fixes): 
  Trades: 31 | WR: ??% | PF: ?? | P&L: -₹26,814 | DD: 5.3%

Step 1 (Wider window 9:50-12:30):
  Trades: __ | WR: __% | PF: __ | P&L: ₹______ | DD: __%

Step 2 (Tiered confidence):
  Trades: __ | WR: __% | PF: __ | P&L: ₹______ | DD: __%

Step 3 (Best ATR config: _______):
  Trades: __ | WR: __% | PF: __ | P&L: ₹______ | DD: __%

Step 4 (Regime filter):
  Trades: __ | WR: __% | PF: __ | P&L: ₹______ | DD: __%

FINAL COMBINED:
  Trades: __ | WR: __% | PF: __ | P&L: ₹______ | DD: __%
==============================================================
```

Save this tracker as `optimization_results_tracker.txt`.

---

## SUCCESS CRITERIA

The backtest PASSES and is ready for 6-month validation if ALL of these are met:

```
[ ] Net P&L is POSITIVE
[ ] Profit Factor > 1.3 (ideally > 1.5)
[ ] Win Rate > 35%
[ ] Max Drawdown < 15% of capital
[ ] Total trades > 40 in 3 months (>3/week average)
[ ] No single day loses > 5% of capital
[ ] At least 2 months out of 3 are individually profitable
[ ] No strategy in whitelist has PF < 0.8
```

If the backtest passes, immediately run the **6-month extension** (Sep 2025 — Feb 2026) with the same config.

---

## WHAT NOT TO DO

1. **DO NOT re-enable Market Structure** — it had 131 trades and lost ₹97K. It's the #1 loss maker. Leave it blacklisted.
2. **DO NOT widen past 12:30** — afternoon sessions are proven losers.
3. **DO NOT lower confidence below 0.80** for any strategy.
4. **DO NOT remove the ATR trailing** — fixed SL was the original fatal bug.
5. **DO NOT add too many strategies at once** — add one at a time and measure impact.
6. **DO NOT overfit** — if a config only works for one specific month, it's overfitting.

---

## START WITH STEP 1. One step at a time. Record everything. GO.
"
Observation: Create successful: /app/GEMINI_PHASE2_OPTIMIZE_TO_PROFIT.md