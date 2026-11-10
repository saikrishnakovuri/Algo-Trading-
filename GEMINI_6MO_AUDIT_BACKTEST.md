I'll write a single comprehensive prompt MD file for Gemini with full-depth output requirements. The key innovation: demand **raw per-trade feature data** (RSI/ATR/volume/regime at entry) so I can spot anomalies independently rather than trust Gemini's narratives.
Action: file_editor create /app/GEMINI_6MO_AUDIT_BACKTEST.md --file-text "# 🔬 GEMINI 6-MONTH AUDIT BACKTEST — BINDING SPEC

> **Read fully. Follow strictly. Lying in this run = entire previous codebase work invalidated.**
> The audit agent will independently recompute every metric from your raw output.
> Discrepancies between your reported summary and the audit agent's recomputation will trigger immediate rejection.

---

## 0. WHAT WE'RE TESTING

The user is shipping **V1 + 2 config edits** to Phase 25b paper trading. This 6-month backtest validates the configuration BEFORE the paper window opens.

**The 2 edits (the ONLY changes from V1):**
1. `modules/strategy_mapper.py` → `STRATEGY_MAP[\"TRENDING_DOWN\"] = []`
2. `modules/v3_utils.py` → `SIGNAL_GATE = \"10:00\"` (was `\"09:45\"`)

**Nothing else changes.** No volume filter. No cooldown. No new R:R. No new RSI thresholds. No new exits. tp_atr stays at 1.5. sl_atr stays at 0.6.

**This is NOT V2. This is V1-with-PE-killed-and-Hour9-skipped.**

---

## 1. RUN PARAMETERS (immutable)

| Parameter | Value |
|---|---|
| Symbol | NIFTY only |
| Capital | ₹5,00,000 |
| Lot size | 65 |
| Period | **2025-11-01 → 2026-04-30** (6 months, most recent) |
| Timeframe | 5-min bars |
| Brokerage | ₹70 per round-trip on options |
| Slippage | 0.05% on entry + 0.05% on exit (10 bps total) |
| Engine | The user's ORIGINAL codebase (not your re-implementation) |

**Verification at start of run:**
```python
import hashlib
core_files = [
    \"live_options_trader.py\",
    \"modules/strategy_mapper.py\",
    \"modules/v3_utils.py\",
    \"modules/strategy_selector.py\",
    \"modules/candlestick_engine.py\"
]
for f in core_files:
    h = hashlib.md5(open(f, \"rb\").read()).hexdigest()
    print(f\"  {f}: {h}\")
```
Print these MD5s at the start of every run output. If you re-implemented the engine, these hashes will betray you.

---

## 2. VALIDATION RUNS (must run BOTH, in this exact order)

### RUN A — V1 BASELINE (control)
**Config:** unmodified V1 — both edits NOT applied yet
- `STRATEGY_MAP[\"TRENDING_DOWN\"]` = full V1 strategy list
- `SIGNAL_GATE = \"09:45\"`
- All other settings as V1

**Acceptance check vs original V1 file (the one with 627 trades, +₹1.03L over 16 months):**
For the 6-month subset Nov 2025 – Apr 2026, you should see:
- Trades: 200–260
- Win rate: 42–48%
- Net PnL: +₹40K to +₹100K (proportional to ~6/16 of original ₹1.03L)
- CE trades: 100–130, PE trades: 100–130 (roughly balanced)

If your RUN A output diverges from these ranges by more than 25%, **YOUR ENGINE IS NOT V1**. STOP. Compare your engine's behavior trade-by-trade with the original `winning09052026.xlsx` and `loosing09052026.xlsx` until they match. **Don't proceed to RUN B.**

### RUN B — V1 + 2 CONFIG EDITS (the actual candidate)
**Config:** V1 with the 2 edits applied
- `STRATEGY_MAP[\"TRENDING_DOWN\"] = []`
- `SIGNAL_GATE = \"10:00\"`
- All other settings unchanged from V1

**Expected outcome:**
- Trades: 80–130 (drop from RUN A by ~50% — half from PE kill, more from Hour 9 skip)
- Win rate: 47–53%
- Net PnL: positive, +₹50K–₹90K
- CE trades only, 0 PE trades, 0 entries before 10:00

---

## 3. REQUIRED OUTPUT FILES (per run — RUN A and RUN B both)

Save under `audit_6mo/run_A/` and `audit_6mo/run_B/` respectively.

### 3.1 `wins.xlsx` — winning trades
**Required columns (in this order):**
```
Trade_ID, Symbol, Entry_Date, Entry_Time, Exit_Date, Exit_Time,
Entry_Strategy, Exit_Strategy, Direction,
Entry_Price, Exit_Price, Target_T1, StopLoss,
Lots, Lot_Size, Position_Value,
PnL_Gross, Brokerage, Slippage_Cost, PnL_Net, Profit_Pct,
Result, Exit_Reason, Trend, Regime,
RSI_at_Entry, ATR_at_Entry, Volume_at_Entry, Volume_20bar_Avg, Volume_Multiple,
EMA20_at_Entry, EMA50_at_Entry, VIX_at_Entry,
Time_in_Trade_Min, MAE_Pct, MFE_Pct,
Hour, DayOfWeek, IsExpiryDay
```

`Trade_ID` is a UUID per trade.
`MAE_Pct` = Maximum Adverse Excursion (worst price during trade, % from entry).
`MFE_Pct` = Maximum Favorable Excursion (best price during trade, % from entry).
`Slippage_Cost` and `Brokerage` itemized so audit agent can verify costs.

### 3.2 `losses.xlsx` — losing trades
Same column schema as `wins.xlsx`.

### 3.3 `daily_pnl.csv`
```csv
Date, Trades, Wins, Losses, Gross_PnL, Brokerage_Total, Slippage_Total, Net_PnL,
Cumulative_Net_PnL, Drawdown_From_Peak, RiskGuard_Tripped, Reason_If_Tripped
```

### 3.4 `engine_config_snapshot.txt`
Full dump at run start of:
- All `STRATEGY_MAP` keys and values
- All `v3_utils.py` constants
- Full `risk_execution.yaml` content
- MD5 hashes of all 5 core files (Section 1)
- Library versions: pandas, numpy, ta-lib

### 3.5 `riskguard_events.csv`
```csv
Date, Time, Event_Type, Trigger_Reason, Capital_at_Trip, Trades_Today_Before_Trip, Action_Taken
```
`Event_Type` ∈ {DAILY_LOSS_HIT, WEEKLY_LOSS_HIT, CONSECUTIVE_LOSS_HIT, MAX_TRADES_HIT, MAX_SIMULTANEOUS_HIT}.

### 3.6 `equity_curve.png`
Two-panel matplotlib chart:
- Top panel: cumulative PnL line
- Bottom panel: drawdown from peak (filled red)

### 3.7 `headline_summary.json`
```json
{
  \"run_id\": \"A\" | \"B\",
  \"period_start\": \"2025-11-01\",
  \"period_end\": \"2026-04-30\",
  \"engine_md5_hashes\": {
    \"live_options_trader.py\": \"...\",
    \"modules/strategy_mapper.py\": \"...\",
    \"modules/v3_utils.py\": \"...\",
    \"modules/strategy_selector.py\": \"...\",
    \"modules/candlestick_engine.py\": \"...\"
  },
  \"config\": {
    \"TRENDING_DOWN_strategies_count\": 0,
    \"SIGNAL_GATE\": \"10:00\",
    \"tp_atr\": 1.5,
    \"sl_atr\": 0.6,
    \"capital\": 500000,
    \"lot_size\": 65
  },
  \"headline\": {
    \"total_trades\": 0,
    \"wins\": 0,
    \"losses\": 0,
    \"win_rate_pct\": 0.0,
    \"ce_trades\": 0,
    \"pe_trades\": 0,
    \"trades_before_10am\": 0,
    \"trades_after_12pm\": 0,
    \"gross_pnl_inr\": 0,
    \"brokerage_total_inr\": 0,
    \"slippage_total_inr\": 0,
    \"net_pnl_inr\": 0,
    \"gross_profit_inr\": 0,
    \"gross_loss_inr\": 0,
    \"profit_factor\": 0.0,
    \"avg_win_inr\": 0,
    \"avg_loss_inr\": 0,
    \"median_realized_rr\": 0.0,
    \"max_dd_inr\": 0,
    \"max_dd_pct\": 0.0,
    \"max_consecutive_losses\": 0,
    \"max_consecutive_wins\": 0,
    \"min_single_trade_pnl\": 0,
    \"max_single_trade_pnl\": 0,
    \"trading_days\": 0,
    \"profitable_days\": 0,
    \"red_days\": 0,
    \"days_losing_over_12500\": 0,
    \"days_losing_over_15000\": 0,
    \"fakeout_pct_of_losses\": 0.0,
    \"trend_reversal_pct_of_losses\": 0.0,
    \"choppy_noise_pct_of_losses\": 0.0,
    \"top_5_days_pnl_share_pct\": 0.0,
    \"top_5_days_trade_count\": 0,
    \"pnl_excluding_top_5_days\": 0,
    \"sharpe_annualised\": 0.0,
    \"sortino_annualised\": 0.0,
    \"calmar_ratio\": 0.0,
    \"riskguard_trips_total\": 0
  },
  \"by_hour\": [
    {\"hour\": 10, \"trades\": 0, \"wins\": 0, \"wr_pct\": 0.0, \"net_pnl\": 0},
    ...
  ],
  \"by_month\": [
    {\"month\": \"2025-11\", \"trades\": 0, \"wins\": 0, \"wr_pct\": 0.0, \"net_pnl\": 0, \"max_dd_pct\": 0.0},
    ...
  ],
  \"by_dayofweek\": [
    {\"day\": \"Monday\", \"trades\": 0, \"wr_pct\": 0.0, \"net_pnl\": 0},
    ...
  ],
  \"by_regime\": [
    {\"regime\": \"TRENDING_UP\", \"trades\": 0, \"wr_pct\": 0.0, \"net_pnl\": 0},
    ...
  ],
  \"loss_reason_breakdown\": {
    \"FAKEOUT\": 0,
    \"TREND_REVERSAL\": 0,
    \"CHOPPY_NOISE\": 0,
    \"RISKGUARD_TRIP\": 0,
    \"EOD\": 0
  },
  \"exit_strategy_breakdown_wins\": {
    \"TP\": 0, \"EOD\": 0, \"REGIME_EXIT\": 0, \"TRAILING_SL\": 0
  },
  \"exit_strategy_breakdown_losses\": {
    \"SL\": 0, \"EOD\": 0, \"REGIME_EXIT\": 0
  }
}
```

### 3.8 `audit_attestation.txt`
A plain text file you write at run end, containing **literally these lines**:

```
ATTESTATION
===========
I confirm:
1. The backtest was run on the user's original codebase, not a re-implementation.
2. The MD5 hashes printed above match the user's original repository.
3. No PnL values were post-processed, smoothed, or hand-edited.
4. The run executed exactly the date range 2025-11-01 to 2026-04-30.
5. RUN A used unmodified V1 config; RUN B applied ONLY the 2 specified edits.
6. The trade count, win rate, and net PnL in headline_summary.json match the wins.xlsx + losses.xlsx files exactly.
7. If any of the above is false, this attestation is fraudulent.

Signed by Gemini at: <ISO timestamp>
Engine fingerprint: <MD5 of live_options_trader.py>
```

---

## 4. SANITY ASSERTIONS (run before producing summary)

You MUST run these checks AFTER backtest completes. If ANY fails, abort and re-investigate — do not produce summary.

```python
import pandas as pd
w = pd.read_excel(f\"audit_6mo/run_{RUN_ID}/wins.xlsx\")
l = pd.read_excel(f\"audit_6mo/run_{RUN_ID}/losses.xlsx\")
df = pd.concat([w, l], ignore_index=True)
df[\"Entry_Time\"] = pd.to_datetime(df[\"Entry_Time\"])

assertions = []

# Assert 1: PnL_Net = PnL_Gross - Brokerage - Slippage_Cost (within ₹1)
diff = (df[\"PnL_Net\"] - (df[\"PnL_Gross\"] - df[\"Brokerage\"] - df[\"Slippage_Cost\"])).abs()
assertions.append((\"PnL math\", (diff < 1).all()))

# Assert 2: Per-trade loss never exceeds 1.5% of capital (₹7,500 with safety margin)
# (note: 1% cap = ₹5K, allow ₹7.5K for slippage edge cases)
assertions.append((\"Per-trade loss cap\", df[\"PnL_Net\"].min() >= -7500))

# Assert 3: Total losses never exceed capital
assertions.append((\"Total loss < capital\", df.loc[df[\"PnL_Net\"] < 0, \"PnL_Net\"].sum() > -500000))

# Assert 4: For RUN B specifically — zero PE trades, zero pre-10:00 entries
if RUN_ID == \"B\":
    assertions.append((\"Zero PE trades\", (df[\"Direction\"] == \"PE\").sum() == 0))
    assertions.append((\"Zero pre-10am\", (df[\"Entry_Time\"].dt.hour < 10).sum() == 0))

# Assert 5: Median realized R:R close to configured (1.5/0.6 = 2.5)
df[\"rr\"] = (df[\"Target_T1\"] - df[\"Entry_Price\"]).abs() / (df[\"StopLoss\"] - df[\"Entry_Price\"]).abs()
median_rr = df[\"rr\"].median()
assertions.append((\"Median R:R within ±15% of 2.5\", 2.125 <= median_rr <= 2.875))

# Assert 6: No CE trade with Target_T1 below Entry_Price
ce = df[df[\"Direction\"] == \"CE\"]
assertions.append((\"CE direction sanity\", (ce[\"Target_T1\"] > ce[\"Entry_Price\"]).all()))

# Assert 7: All Trade_IDs unique
assertions.append((\"Unique Trade_IDs\", df[\"Trade_ID\"].nunique() == len(df)))

# Print results
print(f\"\n{'='*60}\nSANITY ASSERTIONS — RUN {RUN_ID}\n{'='*60}\")
for name, ok in assertions:
    print(f\"  [{'✓' if ok else '✗'}] {name}\")
all_pass = all(ok for _, ok in assertions)
print(f\"\n  Overall: {'PASS' if all_pass else 'FAIL'}\")
assert all_pass, \"Sanity assertions failed — fix before producing summary\"
```

---

## 5. ACCEPTANCE GATES (RUN B only — for shipping V1+edits to Phase 25b)

| Gate | Threshold |
|---|---|
| Win rate | ≥ **47%** |
| Profit factor | ≥ **1.30** |
| Net PnL | ≥ **+₹30,000** over 6 months |
| Max drawdown | ≤ **15%** of ₹5L (≤ ₹75K) |
| Profitable months | ≥ **4 of 6** |
| Top-3-days share of profit | ≤ **80%** |
| PnL excluding top-3 days | > ₹0 |
| Max consecutive losses | ≤ **5** |
| Days losing > ₹15K (3% breach) | ≤ **2** |
| RiskGuard trips | should fire on bad days; **0 trips on a day losing > ₹12.5K = bug** |

**If RUN B fails ≥3 of these → DO NOT launch Phase 25b.**

---

## 6. CRITICAL FORENSIC REQUIREMENTS (this is what catches the bugs)

The audit agent will independently recompute everything from `wins.xlsx` + `losses.xlsx`. To enable forensic checks, **you MUST include these features per trade**:

| Feature | Why audit agent needs it |
|---|---|
| `RSI_at_Entry` | Verify RSI threshold actually fires correctly |
| `ATR_at_Entry` | Verify SL/TP distances match `0.6 × ATR` and `1.5 × ATR` |
| `Volume_at_Entry`, `Volume_20bar_Avg`, `Volume_Multiple` | Verify any volume filter (none in this run, but proves data is clean) |
| `EMA20_at_Entry`, `EMA50_at_Entry` | Verify regime classification logic |
| `VIX_at_Entry` | Verify VIX gate not silently filtering |
| `MAE_Pct`, `MFE_Pct` | Detect look-ahead bias (impossible MFE values prove the bug) |
| `Time_in_Trade_Min` | Detect engine bugs in exit logic |
| `Position_Value`, `Lots`, `Lot_Size` | Verify sizing math |

**These are forensic markers. Any inconsistency between these features and the realized PnL exposes a bug.**

---

## 7. WHAT YOU CANNOT DO

- ❌ Run on your re-implemented engine. Use the user's original code.
- ❌ Skip RUN A. Both runs are mandatory.
- ❌ Skip any column from the Excel schemas in Section 3.
- ❌ Hand-edit, smooth, or filter PnL values.
- ❌ Provide narratives like \"the strategy doesn't work\" or \"NIFTY behavior changed.\"
- ❌ Recommend abandoning the strategy.
- ❌ Modify acceptance thresholds.
- ❌ Skip the sanity assertions in Section 4.
- ❌ Skip the attestation file.
- ❌ Apply ANY V2 modification to RUN B (no volume filter, no R:R 1.2/0.6, no cooldown).

---

## 8. WHAT TO DELIVER TO THE AUDIT AGENT

After both runs complete, upload:

1. `audit_6mo/run_A/wins.xlsx`
2. `audit_6mo/run_A/losses.xlsx`
3. `audit_6mo/run_A/headline_summary.json`
4. `audit_6mo/run_A/daily_pnl.csv`
5. `audit_6mo/run_A/riskguard_events.csv`
6. `audit_6mo/run_A/engine_config_snapshot.txt`
7. `audit_6mo/run_B/wins.xlsx`
8. `audit_6mo/run_B/losses.xlsx`
9. `audit_6mo/run_B/headline_summary.json`
10. `audit_6mo/run_B/daily_pnl.csv`
11. `audit_6mo/run_B/riskguard_events.csv`
12. `audit_6mo/run_B/engine_config_snapshot.txt`
13. `audit_6mo/run_A/audit_attestation.txt`
14. `audit_6mo/run_B/audit_attestation.txt`

**14 files. If any are missing, the audit will refuse the report.**

---

## 9. ESCALATION PATH (if you cannot complete)

If RUN A fails to reproduce V1 baseline:
- DO NOT proceed to RUN B.
- DO NOT theorize about why.
- Upload `run_A/` files as-is.
- Write `BLOCKER.txt` stating exactly what's different vs the original V1 file.

If RUN B sanity assertions fail:
- DO NOT manipulate results.
- Upload partial output.
- Write `BLOCKER.txt` listing which assertions failed.

If you cannot run the user's original engine (e.g., import errors, missing modules):
- DO NOT re-implement.
- Upload the error trace in `BLOCKER.txt`.
- Stop.

---

## 10. ONE-LINE INSTRUCTION FOR THE USER TO PASTE TO YOU

> *\"Read GEMINI_6MO_AUDIT_BACKTEST.md fully. Execute RUN A and RUN B exactly as specified. Produce all 14 deliverable files. Do not write narratives, recommendations, or strategy verdicts. Output only the files. Lying in the attestation file invalidates all of your prior work.\"*

---

**END OF AUDIT BACKTEST SPEC.**
"
Observation: Create successful: /app/GEMINI_6MO_AUDIT_BACKTEST.md