
Action: file_editor create /app/memory_pack/AUDIT_REPORT_pre_paper_trade.md --file-text "# 🛡️ Pre-Paper-Trade Audit — Bug & Risk Report
**Audited zip**: `opus review.zip` (uploaded prior to Phase 25 launch)  
**Auditor**: Architect (Claude / Emergent)  
**Scope**: Root-level Python files, `config/`, `scripts/`, `tests/`, `utils/`  
**Coverage gap**: ⚠️ The `modules/` folder (engines, strategy_mapper, strategy_selector, risk_guard, indicator_cache) was **NOT included in the zip**. Findings below are based on what they CALL into modules, not what's INSIDE modules. A second audit pass on `modules/` is strongly recommended before going live.

---

## 🚨 P0 — CRITICAL (Fix BEFORE Phase 25 launch)

### P0-1. Edge filter is BYPASSED in `scripts/fast_backtest.py`
**File**: `scripts/fast_backtest.py:253-257`
```python
# TEMPORARY: Bypass edge filter for 1L testing as requested
# if expected_pnl < min_edge_required:
#     edge_skipped_count += 1
#     i += 1
#     continue
```
**Why it's critical**: The edge filter is one of the two Phase 24c/24d gates that turned a losing system into a profitable one. With it commented out, **all walk-forward results reported as \"PASS\" may not reflect production behavior**. Phase 24d's \"+₹385K / 7% DD\" claim is suspect until this is re-enabled and re-validated.

**Desired output after fix**:
- Uncomment lines 254-257
- Re-run full walk-forward (5 windows)
- Numbers should match or beat the 24d report. If they don't, our \"validated baseline\" was wrong.
- **STOP**: Do NOT launch Phase 25 paper trade until this filter is active in the same code path used for live trading.

---

### P0-2. Three competing live-trading entry points
**Files**: `live_options_trader.py`, `live_trader_v2.py`, `live_dry_run.py`

`live_trader_v2.py` imports an entirely different selector:
```python
from modules.strategy_selector import StrategySelector   # NOT MasterStrategySelector
```
Phase 20b/21/24d apply to `MasterStrategySelector`. If you accidentally launch `live_trader_v2.py`, **none of the risk gating, regime filtering, or RiskGuard runs**. You could lose capital instantly.

**Why it's critical**: Operator error. Wrong-script launch is a P0 in any production system.

**Desired output after fix**:
- Delete or rename `live_trader_v2.py` → `_archive/live_trader_v2.py.disabled`
- Delete or fold `live_dry_run.py` into `live_options_trader.py` with `PAPER_MODE=true`
- **Only ONE production script**: `live_options_trader.py` — must respect `PAPER_MODE` env var
- Add a startup banner that prints: \"PAPER_MODE=true/false, CAPITAL=₹X, RiskGuard active=Y, VolGate active=Y\"

---

### P0-3. Inconsistent capital across backtest files
| File | Capital used |
|---|---|
| `main_backtest.py:142` | ₹1,000,000 |
| `scripts/fast_backtest.py:123` | ₹500,000 (in simulate_trade) |
| `scripts/fast_backtest.py:214` | ₹100,000 (in RiskGuard init) |
| `scripts/fast_backtest.py:234` | ₹100,000 (in risk_amt) |
| `tests/test_risk_guard.py:15` | ₹50,000 |

**Why it's critical**: Position sizing depends on capital. Inconsistent capital = inconsistent sizes = the \"+₹385K @ 7% DD\" baseline number doesn't correspond to any single repeatable scenario. Phase 25 will produce different results.

**Desired output after fix**:
- Single config key: `risk_execution.yaml → capital: 1000000` (or 500K — your choice)
- All 5 files above read from this single source
- Re-run authoritative 6M with consistent capital
- Document the chosen capital in `memory_pack/06_current_state_and_next_steps.md`

---

### P0-4. Wrong NSE option lot sizes
**Files**: `main_backtest.py:66`, `scripts/fast_backtest.py:77,131`

| Symbol | Used in main_backtest | Used in fast_backtest | **Real NSE lot (as of Feb 2026)** |
|---|---|---|---|
| NIFTY | 65 | 50 | **75** |
| BANKNIFTY | 30 | 25 | **30** |
| FINNIFTY | n/a | 40 | **40** |

**Why it's critical**: Wrong lot size means PnL math is off by 15-50% per trade. Capital deployment is wrong. Margin requirements wrong. RiskGuard triggers wrong.

**Desired output after fix**:
- Centralize lot sizes in `config/instrument_master.yaml`
- All files read from there
- Verify against Angel One's instrument master API on bot startup (NSE updates lot sizes occasionally)
- Re-run authoritative 6M with correct lot sizes

---

### P0-5. Options PnL uses fake constant delta = 0.5
**Files**: `main_backtest.py:64-105`
```python
delta = 0.5
sl_points_option = sl_dist * delta
...
gross_pnl = points_gained * 0.5 * qty
```
**Why it's critical**: Real ATM options delta varies 0.40–0.60 depending on moneyness and time to expiry. ITM/OTM differ massively (0.7-0.9 / 0.1-0.3). Using flat 0.5 makes backtest PnL **systematically inflated for OTM losses and deflated for ITM winners**. Your backtest doesn't tell you what'll happen with real options.

**Desired output after fix**:
- Replace constant 0.5 with a delta-from-moneyness lookup OR a small Black-Scholes approximation
- Track strike, expiry, IV alongside trade — they affect PnL more than spot direction
- OR: simplify by simulating premium-to-premium PnL directly (the way `fast_backtest.py` partially does)
- Re-run 6M with realistic delta model; PnL is likely 20-40% different from current ₹385K baseline

---

### P0-6. Cost computation `premium_proxy = entry × 0.015` is wildly approximate
**File**: `scripts/fast_backtest.py:109`
```python
premium_proxy = entry_price * 0.015
```
For NIFTY at 24,000 spot, this gives ₹360 premium. Real ATM weekly premium ranges from ₹30 (1-day-to-expiry) to ₹250 (4-days-to-expiry). The ₹360 assumption inflates notional and therefore inflates slippage cost.

Compounding issue: `notional_exit = premium_proxy * exit_price / entry_price` (line 75) assumes premium scales LINEARLY with underlying — completely wrong. Real premium scales with delta × spot_move + theta + IV changes.

**Why it's critical**: Cost model affects every PASS/FAIL gate in Phase 24c/d. If real cost is 50% of estimated, Phase 25 will look better than backtest. If 200%, much worse.

**Desired output after fix**:
- Replace with realistic premium model: `premium = max(intrinsic, time_value_table[DTE])` for ATM strike
- For paper trade: capture ACTUAL premium from broker at signal time, use it
- Re-validate Phase 24c/d cost numbers (avg ₹1,943/trade may be off by 2-3×)

---

### P0-7. Vol gate config has `use_india_vix: false` but live MUST use it
**File**: `config/risk_execution.yaml:146`
```yaml
volatility_gate:
  use_india_vix: false           # ← CURRENTLY OFF, using ATR fallback
  fallback_atr_pct_of_price_min: 0.06
```
**Why it's critical**: Backtest ran in ATR fallback mode (because CSVs lack VIX). Live MUST flip to `use_india_vix: true`. If left as-is, live bot will use ATR fallback — which has different sensitivity than VIX. **Phase 25 paper trade is the only place to discover this difference.**

**Desired output after fix**:
- Before Phase 25: verify Angel returns India VIX via `getLTP(\"INDIAVIX\", \"NSE\")`
- Test with both modes once: VIX=true and ATR_fallback=true. Confirm they produce comparable veto counts.
- Live config sets `use_india_vix: true`. Backtest config keeps `false`.
- Add startup log: \"VOL_GATE_MODE=VIX\" or \"VOL_GATE_MODE=ATR_FALLBACK\"

---

### P0-8. PID lock has race condition
**File**: `utils/pid_lock.py:14-43`
```python
if os.path.exists(lock_file):
    ...check...
    sys.exit(1)
# Race window here: another process can also pass the check
with open(lock_file, \"w\") as f:
    f.write(str(os.getpid()))
```
**Why it's critical**: Two operators running the bot at the same time = two sets of orders to broker = double position = potential margin call.

**Desired output after fix**:
```python
import os
try:
    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
except FileExistsError:
    # check if old PID is alive (existing logic)
    ...
```
Atomic `O_EXCL` open is the only race-safe way.

Also: `atexit` does NOT run on `kill -9` or hard crash. Add a heartbeat timestamp inside the lock file and treat stale-by->5min as dead.

---

### P0-9. RiskGuard timezone handling
**Files**: `modules/risk_guard.py` (not in zip), used in `main_backtest.py:172-173`
```python
exit_time = pd.to_datetime(trade['timestamp']) + timedelta(minutes=5 * trade['exit_idx'])
guard.record_trade(pnl=trade['net_pnl'], now=exit_time)
```
Backtest passes tz-aware timestamps. RiskGuard internally does `now.isocalendar()[1]` (line ~78 inferred from spec in memory_pack/02). If RiskGuard internally calls `datetime.now()` without tz, daily/weekly boundaries may misalign vs the trade timestamps.

**Why it's critical**: Daily loss anchor could roll over at the wrong time (e.g., 03:30 UTC instead of midnight IST), letting losing trades from morning leak into a \"new\" trading day and bypass the daily limit.

**Desired output after fix**:
- All datetimes in the bot tz-aware (Asia/Kolkata)
- RiskGuard: `now.astimezone(IST).date()` before computing day_anchor
- Add unit test: trades spanning UTC midnight but same IST date should NOT roll the daily anchor

---

## 🟠 P1 — HIGH (Fix this week)

### P1-1. Symbol universe inconsistent across files
- `main_backtest.py:131`: 8 symbols (incl. INFY, TCS — not in Phase 20b validation)
- `scripts/walk_forward.py:18`: 6 symbols (no FINNIFTY!)
- `scripts/fast_backtest.py:323`: 3 symbols default (NIFTY, BANKNIFTY, RELIANCE)

**Phase 20b was validated on**: NIFTY, BANKNIFTY, FINNIFTY, RELIANCE, HDFCBANK, ICICIBANK, SBIN (7 symbols).

**Fix**: Move to `config/instrument_master.yaml`, single source. Re-run walk-forward with the canonical 7.

---

### P1-2. Walk-forward windows are NOT non-overlapping
- WF4 (Oct-Jan) overlaps WF1 (Oct-Dec) entirely
- WF5 (Dec-Apr) overlaps WF3 (Feb-Apr) entirely

**Why it matters**: True walk-forward demands **independent** segments. With overlap, \"5/5 windows positive\" is misleading — WF4 and WF5 are not independent confirmations.

**Fix**: Use 3 strictly non-overlapping quarters:
```python
WINDOWS = [
    (\"Q4_2025\", \"2025-10-01\", \"2025-12-31\"),
    (\"Q1_2026\", \"2026-01-01\", \"2026-03-31\"),
    (\"Q2_2026\", \"2026-04-01\", \"2026-06-30\"),  # if data available
]
```
3/3 independent = real validation. The 5-window scheme reads PR-friendly but is statistically weaker.

---

### P1-3. Edge-filter math is one-sided
**File**: `scripts/fast_backtest.py:249`
```python
expected_pnl = abs(tp_p - entry_p) * qty * (signal.get('confidence', 50) / 100)
```
This ignores the loss side. Correct expected value:
```python
EV = (win_prob * tp_reward) - (loss_prob * sl_loss)
```
Confidence ≠ historical win rate. A 70%-confidence CANDLESTICK signal has ~50-55% realized WR (from your 6M data).

**Fix**: Replace `signal.confidence/100` with per-strategy historical WR lookup. Or use a conservative blend: `EV = 0.40 × TP_R - 0.60 × SL_R` for trend-following strategies.

---

### P1-4. Force exit at 15:15 throws away last 15 min of session
**File**: `config/risk_execution.yaml:156`
```yaml
session:
  force_exit_at: \"15:15\"
```
Indian market closes 15:30. End-of-day flush of inventory often happens 15:15-15:25 — that's where retail panic-selling creates favorable mean-reversion setups. By forcing exit at 15:15, you're voluntarily missing it. Live brokers also allow MIS positions until 15:20 before auto-square-off.

**Fix**: 
- `force_exit_at: \"15:20\"` (5 min before broker auto-square)
- `no_new_entry_after: \"14:30\"` (gives 50 min for TP/SL)

---

### P1-5. MR `bollinger_reversion.require_rsi_confirm: true` may still over-filter
**File**: `config/mean_reversion.yaml:48`
Phase 17.1c telemetry showed BB_FAIL with reason=RSI_CONFIRM happening at observed RSI=29.32 (legitimately oversold) — the require_rsi_confirm was a contributing blocker. But your final 17.1h config kept it `true`.

**Fix**: This may be intentional (defense-in-depth). But if MR signal frequency in Phase 25 is < 1/week, flip this to `false` and re-validate.

---

### P1-6. Backtest `qty` cap of 500-1000 silently swallowed
**Files**: `main_backtest.py:71`, `scripts/fast_backtest.py:148`
```python
qty = max(1, min(qty, 500))   # main_backtest
qty = max(1, min(qty, 1000))  # fast_backtest
```
If position sizer wants 1500 lots but cap is 500, the EXTRA risk reduction is silent — backtest assumes you traded 500 but lived with 1500's slippage/cost? No — uses capped qty for both. **But you have NO LOG telling you when the cap activates**.

**Fix**: Log every time qty is capped:
```python
if qty < risk_based_qty:
    logger.info(f\"QTY_CAPPED: requested={risk_based_qty} capped={qty} sl_dist={sl_dist}\")
```

---

### P1-7. `orchestrator.py` is dead code or competing system
**File**: `orchestrator.py`
Imports `LearningSystem`, `DecisionEngine`, `AIAnalysisLayer`, `PriceActionEngine`. None of these are mentioned in `memory_pack` or Phase 17-24. Either:
- (a) Dead code — DELETE to avoid confusion
- (b) Active alternative system — INVESTIGATE and reconcile with Phase pipeline

**Fix**: Determine status. If dead, delete. If alive, document or kill.

---

### P1-8. No backtest test suite included
The zip contains `tests/test_risk_guard.py` only. The `test_phases_1_to_10.py` and `test_phase_13_diagnostics.py` referenced in memory_pack are missing. Without these, regressions cannot be detected automatically.

**Fix**: Include and run all 4 test suites in pre-commit hooks:
- `test_phases_1_to_10.py`
- `test_phase_13_diagnostics.py`
- `test_risk_guard.py`
- `test_phase_24d.py` (if exists)

---

## 🟡 P2 — MEDIUM (Fix before Phase 25 day 2, or after paper trade)

### P2-1. Telegram alerts missing rate-limit + retry
If `live_options_trader.py` sends alerts on every guard trip + every order, you'll hit Telegram's 30 msg/sec limit on volatile days. Add a `RateLimitedTelegram` wrapper with token bucket.

### P2-2. Persistence of trades to MongoDB has no failure mode
What happens if Mongo connection drops mid-trade? Either retry-with-backoff or fall back to disk-buffered JSONL.

### P2-3. No daily summary auto-email/Telegram at EOD
At 15:30 every trading day, bot should auto-post: total trades, net PnL, top winner, top loser, RiskGuard state, tomorrow's expected vol regime.

### P2-4. No reconciliation between bot's internal position state and broker's actual position state
Network blip → broker fills an order but bot doesn't know → bot resubmits → double position. Need a 5-min reconciliation loop comparing `broker.get_positions()` to internal state.

### P2-5. ATR multipliers only set for 2 strategies in YAML
`config/risk_execution.yaml:51-53`:
```yaml
strategy_overrides:
  CANDLESTICK:       {sl_atr: 0.6, tp_atr: 1.5}
  MOMENTUM_BREAKOUT: {sl_atr: 1.0, tp_atr: 3.5}
```
VWAP_BOUNCE and MEAN_REVERSION don't have overrides — they fall through to defaults. Document what the default is OR add explicit overrides for ALL 4 active strategies.

### P2-6. Capital growth not modeled
Backtest uses static capital. Real account grows/shrinks. After a +50% month, position sizes should scale up. After -10%, they should scale down. Currently fixed.

**Fix**: Optional. Could amplify the seasonal edge — but also amplifies drawdown. Conservative is fine for paper trade.

### P2-7. No \"kill switch\" Telegram command
You should be able to send `/halt` to your bot's Telegram channel and have it cancel all open orders and stop trading.

---

## 🟢 P3 — LOW (Nice to have)

### P3-1. `main_backtest.py:53` — hardcoded SL fallback bypasses Phase 18
```python
sl_dist = 2 * atr        # hardcoded
```
Should read `strategy_overrides` from yaml.

### P3-2. Empty trailing newlines in YAML files cause some parsers to choke. Trim them.

### P3-3. `print()` statements still in `main_backtest.py:19-21` (Phase 20b verify) — convert to logger.

### P3-4. No CI/CD pipeline. Even a simple GitHub Action that runs pytest on every commit would catch regressions.

### P3-5. `logs/` and `data/` not in `.gitignore` — if you push to GitHub by accident, you leak trade history.

---

## ✅ What I COULD verify (passes basic sanity)

| Item | Status |
|---|---|
| `config/mean_reversion.yaml` final Phase 17.1h state | ✅ Matches memory_pack (BB 1.1, VWAP 0.7, RSI 35/65, anti_trend OFF) |
| `config/risk_execution.yaml` Phase 18 ATR exits | ✅ Present for 2 strategies |
| `config/risk_execution.yaml` Phase 24c per-symbol slippage | ✅ Correctly per-symbol |
| `config/risk_execution.yaml` Phase 24d position cap | ✅ 15% notional / 1% risk |
| `tests/test_risk_guard.py` | ✅ 5/5 covers daily/weekly/streak/cooldown/persistence |
| `walk_forward.py` runs the 5 windows | ✅ But see P1-2 about overlap |
| `paper_trade_aggregate.py` reads JSONL correctly | ✅ Simple, works |

---

## 🎯 What CANNOT be audited (modules/ folder missing)

These files are **referenced everywhere** but NOT in the zip. You MUST audit these manually before paper trade:

1. **`modules/strategy_mapper.py`** — verify Phase 20b kills are still in place (LOW_VOL=[], BREAKOUT_SETUP=[]).
2. **`modules/strategy_selector.py`** (a.k.a. MasterStrategySelector) — verify funnel counters, edge filter wiring, vol gate wiring, risk guard wiring.
3. **`modules/risk_guard.py`** — verify timezone handling, state persistence, cooldown logic.
4. **`modules/indicator_cache.py`** — verify global EWM (not iterative).
5. **`modules/mean_reversion_engine.py`** — verify anti_trend_filter is actually disabled-by-config.
6. **`modules/candlestick_engine.py`** — verify ATR exit overrides read from YAML.
7. **`modules/momentum_engine.py`** — verify same.
8. **`modules/broker_layer.py`** — verify Angel One order placement, error handling, India VIX endpoint.
9. **`modules/options/signal_adapter.py`** — verify Phase 19b indicator cache reads.

---

## 🚦 Final Verdict: NOT READY for Phase 25 paper trade

**Blockers**:
1. P0-1: Edge filter is OFF → re-enable + re-validate walk-forward
2. P0-2: Three live trader paths → consolidate to one
3. P0-3: Capital inconsistent across files → centralize
4. P0-4: Wrong NSE lot sizes → fix to NIFTY=75
5. P0-5: Fake delta=0.5 in main_backtest → use real delta or premium-to-premium
6. P0-7: Vol gate must flip to `use_india_vix: true` for live + verify Angel returns VIX
7. P0-8: PID lock race → atomic O_EXCL
8. P0-9: Timezone-aware RiskGuard

**Suggested sequence**:
1. **Day 1** (4-6 hours): Fix all 8 P0 items
2. **Day 2** (3-4 hours): Re-run authoritative 6M with all fixes; expect baseline to shift ±15% from ₹385K
3. **Day 3**: Address P1-1, P1-2, P1-3, P1-4 (symbol consistency, non-overlapping WF, EV math, force-exit time)
4. **Day 4**: Wire and test Telegram + reconciliation (P2-1 through P2-4)
5. **Day 5**: Launch Phase 25 paper trade with confidence

**Honest expectation after fixes**: The \"+₹385K / 7% DD / OOS PF 1.46\" baseline will likely move to **+₹200K-₹500K / 8-12% DD / OOS PF 1.10-1.40** depending on direction of corrections. That's still tradeable. The point of this audit is to land in TRUTH before risking real capital.

---

## 📋 Quick-fix prompt template for your local executor

When you're ready, ask the architect to issue **Phase 25a — Pre-flight P0 fixes** as a single combined prompt that addresses items P0-1 through P0-9 in one execution pass, then re-runs walk-forward to lock the corrected baseline.

After P0 cleared → Phase 25b — P1 cleanup → Phase 25 paper trade launch.

**Do not skip these fixes**. The cost of one P0 fix at this stage = 30 minutes. The cost of discovering it at live trade = your capital.
"
Observation: Create successful: /app/memory_pack/AUDIT_REPORT_pre_paper_trade.md