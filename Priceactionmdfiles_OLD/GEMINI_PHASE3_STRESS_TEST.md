
Action: file_editor create /app/GEMINI_PHASE3_STRESS_TEST.md --file-text "# PHASE 3: FROM FRAGILE PROFIT TO ROBUST PROFIT
## 6-Month Stress Test + Paper Trading Readiness

Read `PHASE2_RESULTS_ANALYSIS.md` first for full context.

**Current state:** +₹14,894 profit on ₹5L (PF 1.11). Profitable but fragile — depends on 1 strategy, fails in ranging markets, wins capped at TP.

**Goal:** Fix the 6 remaining problems, run 6-month stress test, and prep for paper trading.

---

## FIX 1: REMOVE THE TP CAP — LET WINNERS RUN

This is the #1 priority. Every win on Jan 8 hit exactly ₹15,000 (3R cap). With ATR trailing, there should be NO hard TP. The trailing stop IS the exit.

**In `simulate_trade()`, when `trail: True`, disable the TP check entirely:**

```python
if tp_sl_config.get('trail', False):
    # TRAILING MODE: No fixed TP. Only exit on trailing stop hit.
    # The initial tp_price is just a \"reference\" but NOT an exit trigger.
    
    for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
        current_bar = df.iloc[j]
        
        # Update trailing stop
        if direction == 'BULLISH':
            new_trail = current_bar['close'] - (atr * tp_sl_config['sl_atr'])
            trailing_sl = max(trailing_sl, new_trail)
            
            # ONLY exit on trailing stop — NO TP cap
            if current_bar['low'] <= trailing_sl:
                exit_price = trailing_sl
                exit_time = df.index[j]
                result = \"WIN\" if exit_price > entry_price else \"LOSS\"
                break
        else:  # BEARISH
            new_trail = current_bar['close'] + (atr * tp_sl_config['sl_atr'])
            trailing_sl = min(trailing_sl, new_trail)
            
            if current_bar['high'] >= trailing_sl:
                exit_price = trailing_sl
                exit_time = df.index[j]
                result = \"WIN\" if exit_price < entry_price else \"LOSS\"
                break
else:
    # FIXED TP/SL MODE: Keep the existing logic with TP check
    # (existing code for non-trailing methods)
```

**Expected impact:** Jan 8 winners that were capped at ₹15K could run to ₹25K-₹50K+ in a strong trend. This alone could double the total P&L.

---

## FIX 2: ADD RANGING MARKET DETECTION — STOP TRADING IN CHOP

February's 8.3% win rate happened because the system traded breakouts in a choppy market where every breakout was a fakeout. 

**Add a volatility regime check that pauses trading when the market is ranging:**

```python
def is_market_trending(df, lookback=50):
    \"\"\"
    Returns True if market is trending (safe to trade breakouts).
    Returns False if market is ranging/choppy (skip breakout trades).
    
    Method: ADX-like directional movement check
    \"\"\"
    recent = df.iloc[-lookback:]
    
    # 1. Check if price is making higher highs OR lower lows (trending)
    highs_10 = recent['high'].rolling(10).max()
    lows_10 = recent['low'].rolling(10).min()
    
    expanding_range = (highs_10.iloc[-1] - lows_10.iloc[-1]) > (highs_10.iloc[-20] - lows_10.iloc[-20])
    
    # 2. Check if MA slope is significant
    ma20 = recent['close'].rolling(20).mean()
    ma_slope = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] * 100
    
    # 3. Check ATR expansion (trending = higher ATR)
    atr_recent = (recent['high'] - recent['low']).iloc[-10:].mean()
    atr_older = (recent['high'] - recent['low']).iloc[-30:-20].mean()
    atr_expanding = atr_recent > atr_older * 1.1  # ATR growing by 10%+
    
    # Trending if: range expanding AND (MA slope > 0.1% OR ATR expanding)
    is_trending = expanding_range and (abs(ma_slope) > 0.1 or atr_expanding)
    
    return is_trending

# In the main loop, BEFORE processing signals:
if not is_market_trending(current_window):
    continue  # Skip this bar — market is choppy, breakouts will fail
```

**Expected impact:** This should filter out most of February's losing trades while keeping January and April signals.

---

## FIX 3: EXCLUDE WEDNESDAY (OR ADD DAY-SPECIFIC RULES)

Wednesday lost ₹40,410 while Thursday gained ₹50,137. 

**Option A (Simple): Skip Wednesday entirely**
```python
if current_bar.name.weekday() in [0, 1, 2]:  # Mon, Tue, Wed
    continue
```

**Option B (Smarter): Wednesday-specific tighter filter**
```python
if current_bar.name.weekday() == 2:  # Wednesday
    # Only trade on Wednesday if confidence is very high AND market is strongly trending
    if best_sig.confidence < 0.90:
        continue
    if abs(ma_slope) < 0.2:  # Need stronger trend on Wednesdays
        continue
```

**Recommend Option A first.** Test it. If it hurts trade count too much, switch to Option B.

---

## FIX 4: TIGHTEN TIME WINDOW TO 10:00-11:59

The data is clear:
- 09:00-10:00: 20% win rate, -₹9,653
- 10:00-11:00: 39% win rate, +₹7,565
- 11:00-12:00: **65% win rate, +₹29,090** (BY FAR the best)
- 12:00-13:00: 38% win rate, -₹12,107

**Narrow window to 10:00-12:00 (remove 9:50 start and 12:00-12:30):**

```python
hour = current_bar.name.hour
if hour < 10 or hour >= 12:
    continue
```

**Expected impact:** Lose a few trades but eliminate the 09:00 and 12:00 losers. Net positive.

---

## FIX 5: DISABLE NON-PERFORMING STRATEGIES

Only Breakout-Retest-Continuation is profitable. All others are net negative with <5 trades each. They add noise.

```python
# For this phase, ONLY run the proven strategy
ACTIVE_STRATEGIES = {'Breakout-Retest-Continuation'}

if best_sig.strategy_name not in ACTIVE_STRATEGIES:
    continue
```

**Why:** With only 74 trades, the other strategies (4, 4, 3, 1 trades each) don't have enough data to prove they work. Better to run lean with 1 proven strategy than dilute with unproven ones.

**Re-enable others later** when you have 6+ months of data and each strategy has 20+ trades.

---

## FIX 6: EXTEND LOOKAHEAD FOR TRAILING STOPS

Currently, the lookahead is 100 bars (100 × 5min = 500 min = ~8 hours). For 5-minute data during a 2-hour trading window (10:00-12:00), that's 24 bars of actual trading time.

**Problem:** A trailing stop needs TIME to let the trend develop. 24 bars might not be enough.

**Solution:** Increase lookahead to 200 bars. This gives the trailing stop more room to work, especially for moves that extend over multiple sessions.

```python
# Change from:
for j in range(entry_idx + 1, min(entry_idx + 101, len(df))):
# To:
for j in range(entry_idx + 1, min(entry_idx + 201, len(df))):
```

Also update the EOD exit:
```python
eod_idx = min(entry_idx + 200, len(df) - 1)
```

---

## AFTER ALL 6 FIXES: RUN THE 6-MONTH STRESS TEST

### Configuration

```python
STRESS_TEST_CONFIG = {
    'start_date': '2025-09-01',
    'end_date': '2026-02-28',     # 6 months
    'capital': 500000,
    'risk_pct': 0.01,
    'tp_sl': 'ATR_TRAILING',
    'sl_atr': 2.0,
    'trail': True,
    'tp_hard_cap': None,          # NO TP CAP — trailing stop is the exit
    'lookahead_bars': 200,
    'excluded_days': [0, 1, 2],   # Mon, Tue, Wed
    'trading_hours': (10, 12),    # 10:00-12:00 only
    'min_confidence': 0.85,
    'active_strategies': ['Breakout-Retest-Continuation'],
    'require_trending': True,     # Regime filter: skip choppy markets
}
```

### Run It

```python
results = run_backtest(STRESS_TEST_CONFIG)
```

### Save Results

```
Output files:
1. backtest_6month_detailed_results.csv — Every trade
2. backtest_6month_summary.txt — Performance summary
3. optimization_results_tracker.txt — Append Phase 3 results
```

---

## 6-MONTH SUCCESS CRITERIA

The system is ready for paper trading IF ALL of these pass:

```
[ ] Net P&L is POSITIVE over 6 months
[ ] Profit Factor > 1.3
[ ] Win Rate > 40%
[ ] Max Drawdown < 20%
[ ] At least 4 out of 6 months are individually profitable
[ ] No single month loses more than 10% of starting capital
[ ] Total trades > 50 (statistically meaningful)
[ ] Largest single loss ≤ ₹5,000 (1% risk maintained)
[ ] No loss streak longer than 8 trades
[ ] The system generates trades in at least 5 of 6 months
```

---

## IF 6-MONTH PASSES → PAPER TRADING CHECKLIST

### Broker Connection
```
[ ] API credentials configured (Zerodha/Alpaca)
[ ] Authentication works
[ ] Can fetch live OHLCV data in 5-min timeframe
[ ] Can place paper/test orders
[ ] WebSocket or polling for live candles works
```

### Engine Configuration
```
[ ] PriceActionEngine loads Breakout-Retest-Continuation strategy
[ ] ATR trailing stop implemented correctly (no TP cap)
[ ] Time filter: 10:00-12:00 only
[ ] Day filter: Thursday and Friday only
[ ] Regime filter: skip ranging markets
[ ] Min confidence: 0.85
[ ] Risk: 1% per trade
```

### Risk Management
```
[ ] Max loss per trade: ₹5,000 (1% of capital)
[ ] Max daily loss: ₹15,000 (3%) → stop for day
[ ] Max weekly loss: ₹25,000 (5%) → stop for week
[ ] Max concurrent positions: 2
```

### Logging
```
[ ] Every trade logged to CSV with timestamp, entry, exit, P&L
[ ] Running capital tracked
[ ] Daily summary generated
[ ] Error handling — no crashes, log and continue
```

### Create Run Commands

```markdown
# Paper Trading — Start Commands

## Quick Start
python run_paper_trading.py --config paper_config.yaml --mode PAPER

## Monitor
tail -f logs/paper_trades.csv
tail -f logs/paper_trading.log

## Daily Check
python check_paper_results.py --today

## Stop
Ctrl+C or: python stop_paper_trading.py
```

---

## IMPLEMENTATION ORDER

```
Fix 1: Remove TP cap (let trailing stop be the only exit)
  → Test → Compare P&L to baseline

Fix 2: Add ranging market detection
  → Test → Check if February improves

Fix 3: Exclude Wednesday  
  → Test → Verify P&L improves

Fix 4: Tighten to 10:00-12:00
  → Test → Verify

Fix 5: Single strategy (Breakout-Retest only)
  → Test → Verify

Fix 6: Extend lookahead to 200 bars
  → Test → Verify

COMBINED: Apply all 6 fixes
  → Run 6-month stress test (Sep 2025 - Feb 2026)
  → Check against success criteria
  → If passes → Paper trading setup
```

**After each fix, record results in optimization_results_tracker.txt.**

---

## THE KEY INSIGHT

The system found a **genuine edge**: Breakout-Retest-Continuation with ATR trailing during trending markets on Thursday/Friday mornings. That's a real, specific edge. Don't dilute it with unproven strategies or time windows.

**The goal now is NOT to add more — it's to PROTECT the edge and test it over 6 months.**

## START WITH FIX 1. GO.
"
Observation: Create successful: /app/GEMINI_PHASE3_STRESS_TEST.md