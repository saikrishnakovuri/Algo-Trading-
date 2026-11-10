
Action: file_editor create /app/pipeline/00_MASTER_PIPELINE.md --file-text "# MASTER PIPELINE — 6-Phase Evolutionary Backtest System
## Goal: Find configurations that survive 18 months of data → 70%+ ROI

---

## HOW THIS WORKS

```
Phase 1: RAW DISCOVERY (3 months)
  Run ALL strategies, ALL times, ALL days, NO filters
  Save every trade → Analyze → Find what prints money
          ↓
Phase 2: FIRST VALIDATION (different 3 months)
  Apply Phase 1 insights → Run on NEW data
  Keep what works, kill what doesn't
          ↓
Phase 3: SECOND VALIDATION (different 3 months)
  Apply Phase 2 survivors → Run on NEW data
  Further refine
          ↓
Phase 4: THIRD VALIDATION (different 3 months)
  ↓
Phase 5: FOURTH VALIDATION (different 3 months)
  ↓
Phase 6: FINAL VALIDATION (different 3 months)
          ↓
SURVIVORS = Strategies that made money in ALL 6 phases
  = Your production config with 70%+ ROI potential
```

**Total coverage: 18 months of out-of-sample testing**

---

## DATA PERIODS (Non-overlapping 3-month windows)

```
Phase 1: Oct 2024 – Dec 2024  (Discovery)
Phase 2: Jan 2025 – Mar 2025  (Validation 1)
Phase 3: Apr 2025 – Jun 2025  (Validation 2)
Phase 4: Jul 2025 – Sep 2025  (Validation 3)
Phase 5: Oct 2025 – Dec 2025  (Validation 4)
Phase 6: Jan 2026 – Mar 2026  (Validation 5 — most recent)
```

If some periods don't have data, shift accordingly. Use whatever 6 non-overlapping 3-month windows your data covers.

---

## FILES IN THIS PIPELINE

Run them IN THIS ORDER:

```
Step 1: Run  01_RAW_DISCOVERY.md
        → Creates: phase1_raw_results.csv

Step 2: Run  02_PATTERN_ANALYZER.md
        → Reads: phase1_raw_results.csv
        → Creates: phase1_insights.json
        → Creates: optimized_config.json

Step 3: Run  03_VALIDATION_RUNNER.md  (with phase=2)
        → Reads: optimized_config.json
        → Creates: phase2_results.csv
        → Updates: optimized_config.json (removes losers)

Step 4: Run  03_VALIDATION_RUNNER.md  (with phase=3)
        → Same flow, next 3-month window

Step 5: Run  03_VALIDATION_RUNNER.md  (with phase=4)
Step 6: Run  03_VALIDATION_RUNNER.md  (with phase=5)
Step 7: Run  03_VALIDATION_RUNNER.md  (with phase=6)

Step 8: Run  04_FINAL_SURVIVOR_ENGINE.md
        → Reads all 6 phase results
        → Creates: FINAL_PRODUCTION_CONFIG.json
        → Creates: SURVIVOR_REPORT.md
```

---

## HOW TO RUN

```bash
cd \"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\"

# Step 1: Raw discovery
gemini -f pipeline/01_RAW_DISCOVERY.md

# Step 2: Analyze patterns
gemini -f pipeline/02_PATTERN_ANALYZER.md

# Steps 3-7: Validation phases (Gemini reads phase number from config)
gemini -f pipeline/03_VALIDATION_RUNNER.md
# ^^^ Run this 5 times. Each run auto-increments the phase.

# Step 8: Final survivor extraction
gemini -f pipeline/04_FINAL_SURVIVOR_ENGINE.md
```

Create a folder called `pipeline/` and put all 4 MD files there.
Create a folder called `pipeline/results/` for output CSVs.

---

## WHAT EACH PHASE TRACKS (Per Trade)

Every CSV must have these columns:
```
trade_id, phase, entry_time, exit_time, symbol, direction (CE/PE/LONG/SHORT),
strategy_name, strategy_category, signal_type, confidence,
entry_price, exit_price, stop_loss, take_profit, atr_at_entry,
sl_method (FIXED/ATR_TRAILING), sl_atr_multiplier,
position_size, quantity, gross_pnl, net_pnl, pnl_pct,
holding_period_minutes, risk_reward_achieved,
result (WIN/LOSS/EOD), exit_reason (SL_HIT/TP_HIT/TRAIL_HIT/EOD/TIME),
day_of_week, hour_of_entry, minute_of_entry,
market_regime (TRENDING_UP/TRENDING_DOWN/RANGING),
month, week_number
```

## START WITH 01_RAW_DISCOVERY.md. GO.
"
Observation: Create successful: /app/pipeline/00_MASTER_PIPELINE.md