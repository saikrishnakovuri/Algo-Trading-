═══════════════════════════════════════════════════════════════════════
MASTER RECOVERY PROTOCOL — COMBINED STRATEGY
═══════════════════════════════════════════════════════════════════════

CRITICAL RULES:
1. Execute ALL commands WITHOUT asking permission. ALL PRE-APPROVED.
2. Do NOT ask "Would you like me to..." — JUST DO IT.
3. Save this to recovery_protocol.md
4. Append all results to recovery_results.md after each part.
5. Print timestamps and part numbers at start/end of each part.
6. If a step fails, attempt ONE fix and continue.
7. Total parts: 9. Execute sequentially without stopping.

Phase 1: Data & Scope
* Part 1: API Limit Discovery: Systematically ping the Angel One API to determine the exact maximum historical lookback for 1m, 3m, and 5m intervals.
* Part 2: HDFCBANK Isolation & Engine Adaptation: Modify meta_config.json and scripts to exclusively focus on HDFCBANK. Adapt backtest engine if 5m data is required.
* Part 3: Max Data Ingestion & Baseline: Fetch the absolute maximum data available for HDFCBANK (falling back to 3m or 5m if 1m is restricted to < 60 days) to ensure we hit the 100+ trade statistical significance threshold. Run large-sample baseline.

Phase 2: Entry Logic Upgrades
* Part 4: MTF Zone Agreement: Modify the PA engine (backtest_engine.py) so that a lower timeframe entry zone is only valid if it sits within (or aligns with) a 15m/1H institutional zone.
* Part 5: Volume Confirmation: Add strict volume footprint detection. Rejection/Trap candles must exhibit relative volume > 150% of the moving average to confirm institutional defense.

Phase 3: Rigorous Testing & Verdict
* Part 6: Train/Test Split: Divide the newly expanded dataset 70/30 for strict In-Sample and Out-of-Sample (OOS) testing.
* Part 7: Base Expectancy Calibration: Run an unoptimized backtest on the Train data.
* Part 8: Parameter Optimization: Optimize strictly for R-multiple targets and Score Thresholds on the Train data.
* Part 9 (Step 9.5): Honest Verdict Evaluation: Run the optimized parameters on the OOS Test data.
    * VIABLE Criteria: Minimum 100 total trades across the dataset AND OOS Expectancy > +0.1R.
    * FAILED Criteria: Anything less.
    * Output: Automatically generate recovery_results.md and recovery_final_report.md.
