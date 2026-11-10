
Action: file_editor create /app/GEMINI_FIX_AND_BACKTEST.md --file-text "# FIX BACKTEST ENGINE & RUN PRODUCTION-GRADE BACKTEST

## CONTEXT — READ THIS FIRST

Yesterday, this codebase produced a clean, working backtest with excellent results:
- 192 trades over 4 months, 44.8% win rate, +₹16,20,000 P&L on ₹5L capital
- Top performers: Breakout-Retest-Continuation (+₹5.6L), Head and Shoulders (+₹4.4L), Market Structure (+₹2.65L), Supply & Demand (+₹1.65L), CHOCH (+₹80K)
- Results were saved to `backtest_detailed_results.csv` and `optimized_backtest_results.csv`

Today, the same codebase is broken — the V1 backtest only produced **3 trades in January** with 0% win rate and ₹-1,042 loss. Something broke between yesterday and now.

**Your job: Find what broke, fix it, get back to the working state, and run a clean 3-month backtest.**

---

## STEP 1: DIAGNOSE WHAT BROKE

### 1A — Find yesterday's working state

```bash
# Check git history for what changed
git log --oneline -20
git diff HEAD~1 HEAD --stat
git diff HEAD~3 HEAD --stat

# Find the last commit where backtest worked
# Look for commits around the time optimized_backtest_results.csv was generated
```

Look at these files specifically — one or more of them was modified and broke things:

```
- run_massive_backtest_v2.py (or whatever the main backtest runner is)
- The strategy engine entry point
- Any config files (.yaml, .json, .env)
- Any filter/gate logic files
```

### 1B — Identify the root cause

The V1 run showed these symptoms:
- Only 3 trades triggered (should be ~48/month = ~12/week)
- All 3 were BREAKOUT only (other strategies not firing)
- \"A-tier signals being vetoed by Momentum or Time gates\"

**This means one of these is wrong:**

1. **Momentum filter is too strict** — rejecting valid signals
2. **Time gate is wrong** — blocking trading hours instead of just open/close noise
3. **Strategy detection thresholds changed** — confidence too high, nothing passes
4. **Data feed issue** — not enough candles being loaded, or wrong timeframe
5. **Signal pipeline broken** — strategies detect but signals get dropped before execution

Check each one systematically:

```python
# Debug: Run strategies directly WITHOUT filters to see raw signal count
engine = PriceActionEngine()
df = load_data('NIFTY', '15m', '2026-01-01', '2026-01-31')

# Count raw signals from ALL strategies (no filters)
all_signals = engine.get_all_signals(df, timeframe='15m')
print(f\"Raw signals (no filters): {len(all_signals)}\")

# Now apply filters one-by-one to find which one kills the signals:
after_confidence = [s for s in all_signals if s.confidence >= 0.6]
print(f\"After confidence filter (>=0.6): {len(after_confidence)}\")

after_time = [s for s in after_confidence if is_valid_trading_time(s)]
print(f\"After time filter: {len(after_time)}\")

after_momentum = [s for s in after_time if passes_momentum_check(s)]
print(f\"After momentum filter: {len(after_momentum)}\")

# The filter that causes the biggest drop is your culprit
```

### 1C — Fix it

Once you find the broken filter/gate:
- Compare it to git history (what it looked like yesterday when it worked)
- Revert that specific change or fix the logic
- Do NOT add new filters or change strategy logic — just restore what worked

---

## STEP 2: VERIFY THE FIX WITH A QUICK SANITY CHECK

Before running the full backtest, do a quick 1-week test:

```python
# Quick sanity: Run 1 week of January and verify we get trades
result = backtest(symbol='NIFTY', start='2026-01-06', end='2026-01-10', timeframe='15m')
print(f\"Trades in 1 week: {result['total_trades']}\")  # Should be 8-15 trades
print(f\"Strategies used: {set(t['strategy'] for t in result['trades'])}\")  # Should be multiple strategies

# If still < 5 trades in a week, the fix didn't work. Go back to Step 1.
# If 8+ trades with multiple strategies, proceed to Step 3.
```

---

## STEP 3: RUN THE OPTIMIZED 3-MONTH BACKTEST

Use the EXACT configuration that produced yesterday's good results:

### Configuration

```python
BACKTEST_CONFIG = {
    # Period: 3 months (EXCLUDE March 2026)
    'start_date': '2025-12-01',
    'end_date': '2026-02-28',
    
    # Capital & Risk
    'initial_capital': 500000,          # ₹5 Lakh
    'risk_per_trade_pct': 1.0,          # 1% = ₹5,000 per trade
    'max_open_positions': 5,
    
    # Day Filters (from yesterday's optimized config)
    'excluded_days': ['Monday', 'Tuesday'],    # Avoid weekend volatility noise
    
    # Time Filters
    'excluded_windows': [
        ('09:15', '09:45'),   # Opening noise — skip first 30 min
        ('15:00', '15:15'),   # EOD spikes — skip last 15 min
    ],
    'trading_hours': ('09:45', '15:00'),  # Active trading window
    
    # Exit Method
    'exit_method': 'ATR_TRAILING',       # ATR trailing stop ONLY (this was the winner)
    
    # Strategy Whitelist (top performers from yesterday)
    'strategy_whitelist': [
        'Breakout-Retest-Continuation',
        'Head and Shoulders',
        'Standard Head and Shoulders Pattern',
        'Inverse Head and Shoulders Pattern',
        'Market Structure',
        'Supply & Demand',
        'Change of Character (CHOCH)',
        'Break of Structure (BOS)',
        'Order Blocks',
        'Fair Value Gaps (FVG)',
        'Liquidity Zones',
        'Double Bottom Pattern',
        'Double Top Pattern',
        'Bull Flag Pattern',
        'Bear Flag Pattern',
        'Cup and Handle Pattern',
        'Falling Wedge Pattern',
        'Rising Wedge Pattern',
        'Support',
        'Resistance',
        'Breakout',
        'Retest Entry',
        'Fakeout, Liquidity Grab',
        'Bullish Engulfing Pattern',
        'Bearish Engulfing Pattern',
        'Morning Star Pattern',
        'Evening Star Pattern',
        'Hammer Candlestick Pattern',
        'Shooting Star Pattern',
    ],
    
    # Strategy Blacklist (loss-makers from yesterday)
    'strategy_blacklist': [
        'Ascending Triangle Pattern',
        'Higher High & Higher Low',
        'Spinning Top Candlestick Pattern',
        'Doji Candlestick Pattern',
    ],
    
    # Signal Filters
    'min_confidence': 0.60,              # Only trade 60%+ confidence
    'min_risk_reward': 2.0,              # Minimum 2:1 RR
    
    # Execution Realism
    'slippage_bps': 5,
    'commission_per_order': 20,          # ₹20 per order (Zerodha-like)
    'fill_on_next_candle': True,         # No same-candle fills
    
    # Symbols
    'symbols': ['NIFTY'],               # Start with NIFTY, add BANKNIFTY if clean
    'timeframe': '15m',
    
    # Output
    'output_csv': r'C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\backtest_detailed_results.csv',
}
```

### Run It

```python
results = run_backtest(BACKTEST_CONFIG)
```

### Expected Output (based on yesterday's performance scaled to 3 months)

```
Approximate expectations (3 months, Dec-Feb):
- Total Trades: 130-200 (about 10-15 per week on Wed/Thu/Fri)
- Win Rate: 40-50%
- Net P&L: Positive (₹8L-₹15L range if conditions similar)
- Max Drawdown: < 15%
- Sharpe Ratio: > 1.5
```

If results are wildly different from this, something is still wrong. Debug before saving.

---

## STEP 4: SAVE RESULTS

### 4A — Detailed CSV

Save every trade to `backtest_detailed_results.csv` with these columns:

```
trade_id, date, time, symbol, direction (CE/PE), strategy_name, strategy_category,
confidence, entry_price, exit_price, stop_loss, take_profit,
quantity, gross_pnl, commission, slippage, net_pnl,
holding_period_min, risk_reward_achieved, result (W/L),
running_capital, drawdown_pct, market_regime, exit_reason (SL/TP/ATR_TRAIL/TIME)
```

### 4B — Summary Report

Print AND save a clean summary:

```
============================================================
  BACKTEST RESULTS — OPTIMIZED PRICE ACTION ENGINE
  Period: Dec 1, 2025 → Feb 28, 2026 (3 Months)
  Config: ₹5L Capital | 1% Risk | ATR Trailing | Wed-Fri Only
============================================================

PERFORMANCE
  Initial Capital:      ₹5,00,000
  Final Capital:        ₹XX,XX,XXX
  Net P&L:              ₹XX,XX,XXX (+XX.X%)
  Total Trades:         XXX
  Win Rate:             XX.X%
  Profit Factor:        X.XX
  Sharpe Ratio:         X.XX
  Max Drawdown:         XX.X%
  Avg Win:              ₹XX,XXX (XR)
  Avg Loss:             ₹XX,XXX (1R)
  Best Trade:           ₹XX,XXX (strategy, date)
  Worst Trade:          ₹-XX,XXX (strategy, date)

MONTHLY BREAKDOWN
  Dec 2025:  XX trades | Win XX% | P&L ₹XX,XXX
  Jan 2026:  XX trades | Win XX% | P&L ₹XX,XXX
  Feb 2026:  XX trades | Win XX% | P&L ₹XX,XXX

TOP 5 STRATEGIES BY P&L
  1. Strategy Name — ₹X,XX,XXX (XX trades, XX% win)
  2. ...
  3. ...
  4. ...
  5. ...

BOTTOM 3 STRATEGIES (if any lost money)
  1. ...

TRADE DISTRIBUTION
  Wednesday: XX trades | ₹XX,XXX P&L
  Thursday:  XX trades | ₹XX,XXX P&L
  Friday:    XX trades | ₹XX,XXX P&L

  10:00-11:00: XX trades | ₹XX,XXX P&L
  11:00-12:00: XX trades | ₹XX,XXX P&L
  12:00-13:00: XX trades | ₹XX,XXX P&L
  13:00-14:00: XX trades | ₹XX,XXX P&L
  14:00-15:00: XX trades | ₹XX,XXX P&L
============================================================
```

---

## STEP 5: IF 3-MONTH PASSES → PREP FOR 6-MONTH TEST

If the 3-month backtest shows:
- Positive P&L
- Win rate > 35%
- Sharpe > 1.0
- Max drawdown < 20%
- Profit factor > 1.5

Then immediately set up the 6-month backtest:

```python
SIX_MONTH_CONFIG = BACKTEST_CONFIG.copy()
SIX_MONTH_CONFIG['start_date'] = '2025-09-01'
SIX_MONTH_CONFIG['end_date'] = '2026-02-28'
SIX_MONTH_CONFIG['output_csv'] = r'C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\backtest_6month_detailed_results.csv'

results_6m = run_backtest(SIX_MONTH_CONFIG)
```

Save results to `backtest_6month_detailed_results.csv`.

---

## STEP 6: IF 6-MONTH PASSES → PAPER TRADING READINESS CHECK

Run through this checklist:

```
BROKER CONNECTION
  [ ] API keys present and valid (Zerodha/Alpaca/etc.)
  [ ] Can authenticate successfully
  [ ] Can fetch live OHLCV data
  [ ] Can place paper/test orders
  [ ] WebSocket or polling for live candles works

ENGINE READY
  [ ] PriceActionEngine loads all strategies
  [ ] Analyze() returns signals in < 2 seconds
  [ ] ATR trailing stop logic works on live ticks
  [ ] Day filter (skip Mon/Tue) active
  [ ] Time filter (skip 9:15-9:45, 15:00-15:15) active
  [ ] Blacklisted strategies excluded
  [ ] Min confidence 0.60 enforced
  [ ] Min RR 2.0 enforced

RISK MANAGEMENT
  [ ] Position sizing = 1% of capital per trade
  [ ] Max 5 open positions enforced
  [ ] Daily loss limit (5%) → stop trading for day
  [ ] Stop loss always set on every trade
  [ ] ATR trailing updates on each candle

LOGGING
  [ ] Every trade logged to CSV in real-time
  [ ] Entry/exit prices with timestamps
  [ ] Strategy name and confidence recorded
  [ ] Running P&L tracked
  [ ] Errors logged (don't crash, log and continue)

CONFIG FILE
  [ ] paper_trading_config.yaml exists with all settings
  [ ] Mode = PAPER (NOT LIVE)
  [ ] All the optimized parameters from backtest are in config
```

### Create the run command

Create a file `START_PAPER_TRADING.md` with exact commands to run:

```markdown
# Start Paper Trading

## Prerequisites
1. Ensure broker API keys are set in .env
2. Ensure mode is PAPER (not LIVE)

## Run
python run_paper_trading.py --config paper_trading_config.yaml

## Monitor
- Live trades: tail -f logs/paper_trades.csv
- Engine logs: tail -f logs/paper_trading.log
- Dashboard (if exists): http://localhost:8000

## Stop
Ctrl+C or kill the process
```

---

## RULES

1. **DO NOT add new filters, gates, or logic that wasn't in yesterday's working version.** The goal is to RESTORE what worked, not reinvent.
2. **DO NOT reduce signal sensitivity.** If anything, make it slightly MORE sensitive — yesterday's config with 192 trades in 4 months is the target rate.
3. **DO NOT skip the sanity check (Step 2).** If 1-week test shows < 5 trades, the fix is wrong.
4. **DO NOT hardcode trade results.** Every number must come from actual strategy detection on real candle data.
5. **ATR_TRAILING is the exit method.** Do not switch to fixed SL/TP — ATR trailing is what made yesterday's results work (5R+ winners).
6. **Save everything.** CSV, summary report, logs. I need to verify every number.

## START WITH STEP 1. FIX THE BUG FIRST. THEN BACKTEST. GO.
"
Observation: Create successful: /app/GEMINI_FIX_AND_BACKTEST.md