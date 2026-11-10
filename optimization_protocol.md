═══════════════════════════════════════════════════════════════════════
MASTER OPTIMIZATION PROTOCOL — AUTONOMOUS EXECUTION
═══════════════════════════════════════════════════════════════════════

CRITICAL RULES FOR THE ENTIRE SESSION:
1. Execute ALL PowerShell/Python commands WITHOUT asking for 
   permission. The user has pre-approved EVERY command in this file.
2. Do NOT ask "Would you like me to..." — just DO IT.
3. Do NOT stop between parts unless there is a fatal crash.
4. Save this entire prompt to optimization_protocol.md for reference.
5. After completing each part, write results to 
   optimization_results.md (append, don't overwrite).
6. If any step fails, log the error, attempt a fix, and continue.
   Only stop if 3 consecutive fixes fail for the same step.
7. At the start of each part, print: 
   "=== EXECUTING PART [N] of 11 ==="
8. At the end of each part, print:
   "=== PART [N] COMPLETE — RESULTS LOGGED ==="
9. Time yourself: print timestamps at start and end of each part.
10. DO NOT ask the user anything. All decisions are pre-approved.

═══════════════════════════════════════════════════════════════════════
PART 1 of 11 — FETCH 6 MONTHS OF HISTORICAL DATA
═══════════════════════════════════════════════════════════════════════

GOAL: Get the longest possible historical dataset. Recent 2 months 
(March-April 2026) had global tensions and unusual volatility. We 
need data from calmer AND volatile periods to test robustness.

STEP 1.1: Check Angel One API limits for historical data.
  - What is the maximum lookback for 1-minute candles?
  - What is the maximum lookback for 5-minute candles?
  - What is the maximum lookback for daily candles?
  Print the limits.

STEP 1.2: Fetch the MAXIMUM available 1-minute data for these 25 stocks:
  RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS, ITC, SBIN, BHARTIARTL,
  BAJFINANCE, LT, KOTAKBANK, AXISBANK, MARUTI, TATAMOTORS, WIPRO,
  HCLTECH, SUNPHARMA, POWERGRID, NTPC, ULTRACEMCO, TITAN, ASIANPAINT,
  ADANIPORTS, HINDALCO, JSWSTEEL

  Save each to data/angel_historical/{SYMBOL}_1m.csv
  
  Rate limit: 0.4 seconds between API calls. Use retry with backoff.
  If a symbol fails, skip it and continue. Log skipped symbols.

STEP 1.3: Fetch Nifty 50 index data for the same period:
  - Daily OHLCV → data/nifty50_daily.csv
  - 5-minute OHLCV → data/nifty50_5m.csv (if API supports index intraday)

STEP 1.4: Fetch India VIX daily data:
  - Daily close → data/india_vix_daily.csv
  - If Angel One doesn't provide VIX, try nsepython or any other 
    available source. If nothing works, create a placeholder with 
    VIX=15 and log "VIX DATA: PLACEHOLDER USED"

STEP 1.5: Report data inventory:
  For each symbol, print:
    {SYMBOL}: {start_date} to {end_date}, {N_sessions} sessions, {N_rows} rows
  
  Print total: "{N} symbols fetched, {N} sessions average, date range: X to Y"

VERIFICATION: Confirm at least 15 symbols have 40+ sessions of data.
If fewer than 15 symbols: log warning but continue.

═══════════════════════════════════════════════════════════════════════
PART 2 of 11 — ESTABLISH CLEAN BASELINE (NO FILTERS, HONEST NUMBERS)
═══════════════════════════════════════════════════════════════════════

GOAL: Run a completely UNFILTERED backtest to measure the raw signal 
quality of the PA engine. This is our control group.

STEP 2.1: Create a temporary config override that DISABLES all filters:
  - Afternoon CE block: OFF
  - Momentum filter: OFF
  - Zone respect minimum: OFF (accept all zones)
  - Nifty penalty: OFF (delta = 0)
  - Strategy filter: ALL strategies enabled on ALL symbols
  - Time stops: KEEP (graduated 20/45/90/150 — these are exits, not filters)
  - Score threshold: Use the current base (whatever is in config)

STEP 2.2: Run backtest with 1.5R target on ALL available symbols, 
  ALL available dates:
  
  python run_backtest.py --symbols [all fetched symbols] --days [max]

STEP 2.3: Run SAME backtest with 2.0R target (change only the target).

STEP 2.4: Run SAME backtest with 1.0R target (change only the target).

STEP 2.5: Report RAW BASELINE table:

  ┌──────────┬────────┬───────┬────────┬──────────┬──────────┐
  │ Target   │ Trades │ Win%  │ RR     │ Expect(R)│ P&L      │
  ├──────────┼────────┼───────┼────────┼──────────┼──────────┤
  │ 1.0R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  │ 1.5R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  │ 2.0R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  └──────────┴────────┴───────┴────────┴──────────┴──────────┘

This tells us the OPTIMAL target R-multiple for the PA engine's 
natural signal quality. Pick the target with the highest expectancy.

VERIFICATION: Total trades should be 100+ across all symbols/dates.
If fewer than 50 trades at any target level, the threshold is too 
high — lower it to 4.5 and re-run.

═══════════════════════════════════════════════════════════════════════
PART 3 of 11 — SPLIT DATA INTO TRAIN AND TEST PERIODS
═══════════════════════════════════════════════════════════════════════

GOAL: Prevent overfitting by splitting data into in-sample (train) 
and out-of-sample (test). All optimization happens on TRAIN only. 
TEST is held sacred until Part 10.

STEP 3.1: Determine the full date range from Part 1.
  Split 70/30:
  - TRAIN: First 70% of sessions (older data)
  - TEST: Last 30% of sessions (recent data, includes the volatile period)

  Print: "TRAIN: {start} to {end} ({N} sessions)"
  Print: "TEST: {start} to {end} ({N} sessions)"

STEP 3.2: Create a helper function in run_backtest.py that accepts 
  --start-date and --end-date parameters so we can run backtests 
  on specific date ranges:

  python run_backtest.py --symbols ... --start-date 2025-11-01 --end-date 2026-03-15

STEP 3.3: Re-run the baseline (Part 2) on TRAIN period only.
  Use the BEST target from Part 2.
  Report the same table but for TRAIN data only.

VERIFICATION: TRAIN period should have at least 60+ trades.

═══════════════════════════════════════════════════════════════════════
PART 4 of 11 — TARGET R-MULTIPLE OPTIMIZATION (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Find the exact optimal target that maximizes expectancy.

STEP 4.1: Run backtests on TRAIN data with these targets:
  0.8R, 1.0R, 1.2R, 1.5R, 1.8R, 2.0R, 2.5R, 3.0R

  For each, record: Trades, Win%, RR, Expectancy, P&L

STEP 4.2: Report the optimization table:

  ┌──────────┬────────┬───────┬────────┬──────────┬──────────┐
  │ Target   │ Trades │ Win%  │ RR     │ Expect(R)│ P&L      │
  ├──────────┼────────┼───────┼────────┼──────────┼──────────┤
  │ 0.8R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  │ 1.0R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  │ ...      │  ...   │ ...   │ ...    │ ...      │ ...      │
  │ 3.0R     │  ???   │ ???%  │ ???    │ ???      │ ???      │
  └──────────┴────────┴───────┴────────┴──────────┴──────────┘

STEP 4.3: Select the BEST target (highest expectancy with 20+ trades).
  Lock it for all subsequent parts.
  Print: "OPTIMAL TARGET: {X}R — Expectancy: {Y}R on {N} trades"

VERIFICATION: The best target should have positive expectancy.
If ALL targets are negative: the PA engine needs fundamental work.
Log this finding and continue anyway — the filter optimization in 
Parts 5-7 may still improve things.

═══════════════════════════════════════════════════════════════════════
PART 5 of 11 — FILTER SENSITIVITY MATRIX (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Test each filter INDIVIDUALLY to measure its isolated impact.
Use the optimal target from Part 4.

STEP 5.1: Run 7 backtests on TRAIN data. Each adds ONE filter 
to the unfiltered baseline:

  A. Baseline (no filters) — already have from Part 3
  B. + Afternoon CE block only (no CE after 11:30 unless score >= 7)
  C. + Momentum filter only (last 3 bars must align)
  D. + Zone respect >= 0.50 only
  E. + Zone respect >= 0.65 only
  F. + Nifty penalty -0.5 only
  G. + Strategy filter only (ZONE_REJECTION restricted to banks)

STEP 5.2: Report the filter impact matrix:

  ┌────────────────────────┬────────┬───────┬──────────┬──────────┐
  │ FILTER                 │ Trades │ Win%  │ Expect(R)│ Delta    │
  ├────────────────────────┼────────┼───────┼──────────┼──────────┤
  │ A. No filters          │  ???   │ ???%  │ ???      │ baseline │
  │ B. +Afternoon CE       │  ???   │ ???%  │ ???      │ +???     │
  │ C. +Momentum           │  ???   │ ???%  │ ???      │ +???     │
  │ D. +ZoneResp 0.50      │  ???   │ ???%  │ ???      │ +???     │
  │ E. +ZoneResp 0.65      │  ???   │ ???%  │ ???      │ +???     │
  │ F. +Nifty -0.5         │  ???   │ ???%  │ ???      │ +???     │
  │ G. +Strategy filter    │  ???   │ ???%  │ ???      │ +???     │
  └────────────────────────┴────────┴───────┴──────────┴──────────┘

STEP 5.3: RANK filters by expectancy improvement (Delta column).
  The top 3 filters that improve expectancy the most will be 
  combined in Part 6.

  Print: "TOP 3 FILTERS: {1}, {2}, {3}"
  Print: "NEGATIVE IMPACT FILTERS (hurt performance): {list}"

VERIFICATION: At least 2 filters should show positive delta.
If no filter helps, the issue is purely in signal quality.

═══════════════════════════════════════════════════════════════════════
PART 6 of 11 — OPTIMAL FILTER COMBINATION (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Combine the top filters from Part 5 and find the best combo.

STEP 6.1: Take the top 3 filters from Part 5. Run these combinations:
  - Top 1 alone
  - Top 1 + Top 2
  - Top 1 + Top 2 + Top 3
  - All filters combined
  - Top 1 + Top 3 (skip Top 2)

STEP 6.2: Report combination table:

  ┌────────────────────────┬────────┬───────┬──────────┬──────────┐
  │ COMBINATION            │ Trades │ Win%  │ Expect(R)│ P&L      │
  ├────────────────────────┼────────┼───────┼──────────┼──────────┤
  │ Filter 1 only          │  ???   │ ???%  │ ???      │ ???      │
  │ Filter 1+2             │  ???   │ ???%  │ ???      │ ???      │
  │ Filter 1+2+3           │  ???   │ ???%  │ ???      │ ???      │
  │ All filters            │  ???   │ ???%  │ ???      │ ???      │
  │ Filter 1+3             │  ???   │ ???%  │ ???      │ ???      │
  └────────────────────────┴────────┴───────┴──────────┴──────────┘

STEP 6.3: Select the BEST combination:
  - Must have positive expectancy
  - Must have 15+ trades (statistical minimum)
  - Prefer higher expectancy over higher trade count

  Lock this as the FINAL CONFIGURATION.
  Print: "OPTIMAL CONFIG: Target={X}R, Filters={list}, Expect={Y}R"

═══════════════════════════════════════════════════════════════════════
PART 7 of 11 — SCORE THRESHOLD OPTIMIZATION (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Find the optimal score threshold with the locked filter combo.

STEP 7.1: Using the optimal filters from Part 6, run backtests with 
  these thresholds (modify base_ranging in the config):
  4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0

STEP 7.2: Report threshold table:

  ┌───────────┬────────┬───────┬──────────┬──────────┐
  │ Threshold │ Trades │ Win%  │ Expect(R)│ P&L      │
  ├───────────┼────────┼───────┼──────────┼──────────┤
  │ 4.0       │  ???   │ ???%  │ ???      │ ???      │
  │ 4.5       │  ???   │ ???%  │ ???      │ ???      │
  │ ...       │  ...   │ ...   │ ...      │ ...      │
  │ 7.0       │  ???   │ ???%  │ ???      │ ???      │
  └───────────┴────────┴───────┴──────────┴──────────┘

STEP 7.3: Select optimal threshold (highest expectancy with 10+ trades).
  Update the final config.

═══════════════════════════════════════════════════════════════════════
PART 8 of 11 — PER-STOCK PERFORMANCE ANALYSIS (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Identify which stocks the system works on and which it doesn't.

STEP 8.1: Using the FINAL config (optimal target + filters + threshold),
  run backtest and report per-stock breakdown:

  ┌──────────────┬────────┬───────┬──────────┬──────────┐
  │ STOCK        │ Trades │ Win%  │ Expect(R)│ P&L      │
  ├──────────────┼────────┼───────┼──────────┼──────────┤
  │ RELIANCE     │  ???   │ ???%  │ ???      │ ???      │
  │ HDFCBANK     │  ???   │ ???%  │ ???      │ ???      │
  │ ...          │  ...   │ ...   │ ...      │ ...      │
  └──────────────┴────────┴───────┴──────────┴──────────┘

STEP 8.2: Classify stocks:
  - GREEN (positive expectancy, 3+ trades): KEEP
  - YELLOW (near zero, or < 3 trades): MONITOR
  - RED (negative expectancy, 3+ trades): REMOVE from universe

STEP 8.3: Create the OPTIMIZED UNIVERSE — only GREEN stocks.
  Update config/strategy_filter.yaml accordingly.
  Print: "OPTIMIZED UNIVERSE: {list of GREEN stocks}"

═══════════════════════════════════════════════════════════════════════
PART 9 of 11 — SETUP TYPE ANALYSIS (TRAIN ONLY)
═══════════════════════════════════════════════════════════════════════

GOAL: Identify which setup types work and which don't.

STEP 9.1: From the FINAL config backtest, report per-setup breakdown:

  ┌─────────────────┬────────┬───────┬──────────┬──────────┐
  │ SETUP TYPE      │ Trades │ Win%  │ Expect(R)│ P&L      │
  ├─────────────────┼────────┼───────┼──────────┼──────────┤
  │ TRAP_REVERSAL   │  ???   │ ???%  │ ???      │ ???      │
  │ ZONE_REJECTION  │  ???   │ ???%  │ ???      │ ???      │
  │ PULLBACK        │  ???   │ ???%  │ ???      │ ???      │
  │ OB_MITIGATION   │  ???   │ ???%  │ ???      │ ???      │
  │ ...             │  ...   │ ...   │ ...      │ ...      │
  └─────────────────┴────────┴───────┴──────────┴──────────┘

STEP 9.2: Disable any setup type with negative expectancy AND 5+ trades.
  Update config/strategy_filter.yaml.

═══════════════════════════════════════════════════════════════════════
PART 10 of 11 — OUT-OF-SAMPLE VALIDATION (TEST PERIOD — SACRED)
═══════════════════════════════════════════════════════════════════════

GOAL: This is the moment of truth. Run the FINAL optimized config 
on the TEST period (last 30% of data) that was NEVER used for any 
optimization decisions.

STEP 10.1: Run the FINAL config on TEST period:
  python run_backtest.py --symbols [GREEN stocks only] 
    --start-date [TEST start] --end-date [TEST end]

STEP 10.2: Report the ULTIMATE comparison:

  ┌──────────────┬──────────────┬──────────────┬──────────────────┐
  │ METRIC       │ RAW BASELINE │ TRAIN OPTIMIZED│ TEST (OOS)      │
  ├──────────────┼──────────────┼──────────────┼──────────────────┤
  │ Total Trades │  ???         │  ???          │ ???              │
  │ Win Rate     │  ???%        │  ???%         │ ???%             │
  │ RR Ratio     │  ???         │  ???          │ ???              │
  │ Expectancy   │  ???         │  ???          │ ???              │
  │ P&L          │  ???         │  ???          │ ???              │
  │ Max DD       │  ???         │  ???          │ ???              │
  │ Sharpe       │  ???         │  ???          │ ???              │
  └──────────────┴──────────────┴──────────────┴──────────────────┘

STEP 10.3: VERDICT:
  - If TEST expectancy > +0.2R → SYSTEM IS VIABLE. Proceed to paper.
  - If TEST expectancy is 0 to +0.2R → MARGINAL. Needs more data.
  - If TEST expectancy < 0 → OVERFIT. The optimization didn't 
    generalize. The PA engine needs fundamental changes.

═══════════════════════════════════════════════════════════════════════
PART 11 of 11 — FINAL REPORT & DEPLOYMENT CONFIG
═══════════════════════════════════════════════════════════════════════

GOAL: Compile everything into a single deployment-ready state.

STEP 11.1: Save the FINAL optimized config to config/production.yaml:
  - Optimal target R-multiple
  - Optimal score threshold
  - Active filters (with parameters)
  - Optimized stock universe (GREEN only)
  - Active setup types
  - All risk parameters

STEP 11.2: Write the COMPLETE optimization report to 
  optimization_final_report.md with:
  
  - Data inventory (symbols, date ranges, sessions)
  - Raw baseline performance
  - Each filter's individual impact
  - Optimal combination found
  - Per-stock classification
  - Per-setup classification
  - Train vs Test comparison
  - Final verdict
  - Recommended next steps

STEP 11.3: Update run_live.py to load config/production.yaml 
  as the authoritative configuration for live/paper trading.

STEP 11.4: Print the FINAL SUMMARY:

  ═══════════════════════════════════════════════════════
  OPTIMIZATION COMPLETE
  ═══════════════════════════════════════════════════════
  Data: {N} symbols, {N} sessions, {date range}
  Optimal Target: {X}R
  Optimal Threshold: {X}
  Active Filters: {list}
  Universe: {list of GREEN stocks}
  Active Setups: {list}
  
  TRAIN Performance: {trades}, {win%}, {expect}R, {P&L}
  TEST Performance:  {trades}, {win%}, {expect}R, {P&L}
  
  VERDICT: {VIABLE / MARGINAL / OVERFIT}
  ═══════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════
EXECUTION INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════

1. Save this entire prompt to optimization_protocol.md
2. Create optimization_results.md for logging results
3. Execute Parts 1 through 11 IN ORDER
4. Do NOT skip any part
5. Do NOT ask for confirmation at ANY point
6. If a backtest takes more than 30 minutes, reduce the symbol 
   list to the top 15 by liquidity and continue
7. After each part, append results to optimization_results.md
8. If a part produces unexpected results (e.g., 0 trades), 
   investigate briefly (2 minutes max), attempt ONE fix, 
   and continue
9. Total expected runtime: 2-4 hours
10. START NOW. Begin with Part 1.
═══════════════════════════════════════════════════════════════════════
