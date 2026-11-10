
Action: file_editor create /app/PHASE_25B_LAUNCH_PREP.md --file-text "# 🚀 PHASE 25B FINAL LAUNCH PREP — TOMORROW MORNING PAPER TRADE
**Author:** Audit Agent (Emergent E1) | **Recipient:** Gemini local agent | **Operator:** Project owner
**Target:** Live paper trading starts tomorrow at 09:15 IST | **Capital:** ₹1,00,000 (NOT ₹5L)

---

## 0. FULL CONTEXT YOU MUST INTERNALIZE BEFORE TOUCHING ANY FILE

Read this section completely. Do not skim. The audit agent has spent ~14 turns building this context, catching 5+ fabrications from your previous sessions, and has now arrived at firm truths. Treat these as non-negotiable facts.

### 0.1 What the strategy actually is (V1)

The system is a **regime-gated options trading bot for NSE NIFTY** using Angel One SmartAPI. The proven strategy = **CANDLESTICK retest-confirmation entry** in TRENDING_UP regime + **VWAP_BOUNCE/CANDLESTICK/MOMENTUM_BREAKOUT** in TRENDING_DOWN, with R:R = 1.5R/0.6R (tp_atr=1.5, sl_atr=0.6).

### 0.2 What the trusted V1 numbers are

From `winning09052026.xlsx` + `loosing09052026.xlsx` (the May 9 trusted backtest), filtered to **Nov 1 2025 – Apr 30 2026** (the 6 months immediately before today):

| Metric | Trusted V1 baseline |
|---|---|
| Total trades | 215 |
| Win rate | **51.16%** |
| Net PnL on ₹5L | **+₹1,96,542** (39.3% ROI over 6 mo) |
| Avg win | ₹4,847 |
| Avg loss | −₹3,206 |
| Realized R:R | 1.51 (matches config) |
| Trading days | 113 |
| CE / PE split | 108 / 107 (balanced) |

This is the **ground truth**. Any V2 / V3 / re-implementation result that contradicts this is wrong, not the baseline.

### 0.3 What is FALSE (do not propagate these claims)

Previous sessions of yours produced these false conclusions. They are now disproven. **Do not cite them, repeat them, or build logic around them:**

- ❌ \"The strategy doesn't work for NIFTY\"
- ❌ \"V1 had a hidden R:R bug that inflated win rate\"
- ❌ \"10bps slippage destroys V1 edge\"
- ❌ \"Retest is a contrarian/anti-indicator for NIFTY\"
- ❌ \"Volume-backed retest is statistically a reversal signal\"
- ❌ \"11% win rate proves NIFTY behavior changed\"

All of the above were either fabricated narratives or buggy V2 reimplementations. The V1 file (which you did not generate, but which exists on disk) shows real edge.

### 0.4 What is TRUE (operate from these facts)

- ✅ V1 codebase in `C:\Users\91810\OneDrive\Desktop\AlgoTrading Options` is intact (audited)
- ✅ V1 config has been edited correctly: `SIGNAL_GATE=10:00`, `MAX_TRADES_PER_DAY=4`, `DAILY_LOSS_LIMIT_PCT=0.025`, `COOLDOWN_AFTER_2_LOSSES_MIN=60`
- ⚠️ Second V2 edit (`STRATEGY_MAP[\"TRENDING_DOWN\"]=[]`) was NOT yet applied — operator's choice whether to apply
- ✅ Your previous V2 backtest engine produces 5× fewer signals than V1 and includes Sunday trades — your engine is broken, not the strategy
- ✅ Dashboard work (UNIFIED_DASHBOARD_INTEGRATION_SPEC.md + BACKEND_TO_UI_COMPLETENESS_AUDIT.md) is in progress
- ✅ Operator wants paper trading to start tomorrow with ₹1L capital

### 0.5 What the operator wants from this session

A single integrated state ready for paper trading at 09:15 IST tomorrow. That means:
1. Dashboard is functional (frontend + backend running locally)
2. All backend components have UI (Phase 25 audit completed)
3. Live trader is connected to dashboard for start/stop/monitor
4. Pre-flight checklist is run successfully
5. Operator can launch with one click tomorrow at 09:14 IST

---

## 1. WHAT YOU MUST COMPILE / FINISH TODAY

### 1.1 Three prior specs are your input

These documents already exist in the operator's working directory:

| File | Purpose | Status |
|---|---|---|
| `RETEST_BACKTEST_PROMPT.md` | V2 backtest spec (parametric variants) | Reference only — V2 abandoned |
| `UNIFIED_DASHBOARD_INTEGRATION_SPEC.md` | Frontend + backend dashboard architecture | **Build per this** |
| `BACKEND_TO_UI_COMPLETENESS_AUDIT.md` | 7-phase audit to ensure no backend component is missing UI | **Run per this** |

Your job: **compile/build everything these specs require, in one shot, leaving nothing for tomorrow morning.**

### 1.2 Compilation checklist (every file Gemini must produce / verify exists)

#### Backend (`AlgoTradingTelegramBotAndFrontend/backend/`)
- [ ] `server.py` — extended with `app.include_router()` lines only (no logic edits)
- [ ] `routers/__init__.py`
- [ ] `routers/configs.py` — GET list, GET file, POST file (with auto-backup), POST revert
- [ ] `routers/backtest.py` — POST run, GET status, GET result, GET history
- [ ] `routers/trades.py` — GET live, GET history (date range)
- [ ] `routers/live_pnl.py` — WebSocket `/ws/live-pnl` (5s push)
- [ ] `routers/system.py` — POST start, POST stop, POST kill-switch, GET status
- [ ] `routers/docs.py` — GET list, GET file, GET search
- [ ] `routers/logs.py` — GET tail, WebSocket `/ws/logs`
- [ ] `routers/strategies.py` — GET list (from STRATEGY_MAP), POST toggle, POST min_confidence
- [ ] `routers/riskguard.py` — GET state, POST limits, POST reset
- [ ] `routers/regime.py` — GET current, GET history, POST thresholds
- [ ] `routers/notifications.py` — GET subscriptions, POST toggle, POST test-send
- [ ] `utils/yaml_io.py` — safe read/write with backup
- [ ] `utils/jsonl_tailer.py` — async tailer
- [ ] `utils/subprocess_runner.py` — managed subprocess
- [ ] `utils/v3_utils_io.py` — safe read of v3_utils.py constants (regex-based, NOT import — to avoid modifying the file)
- [ ] `utils/locked_files.py` — MD5 verification module
- [ ] `requirements_dashboard.txt` — additional pip dependencies

#### Frontend (`AlgoTradingTelegramBotAndFrontend/frontend/`)
- [ ] `package.json` + `vite.config.js` + `index.html`
- [ ] `src/App.jsx` — tab router
- [ ] `src/api.js` — centralized fetch helpers
- [ ] `src/ws.js` — WebSocket client with auto-reconnect
- [ ] `src/components/DashboardTab.jsx`
- [ ] `src/components/LivePnLTab.jsx`
- [ ] `src/components/TradesTab.jsx`
- [ ] `src/components/BacktestTab.jsx`
- [ ] `src/components/ConfigsTab.jsx`
- [ ] `src/components/SystemSettingsTab.jsx` — v3_utils constants editor
- [ ] `src/components/StrategiesTab.jsx` — STRATEGY_MAP editor
- [ ] `src/components/RiskGuardTab.jsx`
- [ ] `src/components/RegimeTab.jsx`
- [ ] `src/components/NotificationsTab.jsx`
- [ ] `src/components/CalendarTab.jsx` — no-trade dates editor
- [ ] `src/components/UniverseTab.jsx`
- [ ] `src/components/LogsTab.jsx`
- [ ] `src/components/DocsTab.jsx`
- [ ] `src/components/SaveBar.jsx` — floating Save/Revert with dirty tracking, Ctrl+S
- [ ] `src/components/KillSwitch.jsx` — red emergency stop button
- [ ] `src/styles/theme.css`

#### Audit artifacts (per BACKEND_TO_UI_COMPLETENESS_AUDIT.md)
- [ ] `backend_inventory_v1.json` + `v2` + `FINAL`
- [ ] `frontend_inventory_v1.json` + `v2` + `FINAL`
- [ ] `gap_report_v1.json` + `v2` + `v3_reverse` + `FINAL` + `POST_REMEDIATION_v1`
- [ ] `network_audit_FINAL.json`
- [ ] `click_through_audit_<tab>.json` × 14 tabs
- [ ] `BACKEND_TO_UI_COMPLETENESS_ATTESTATION.md`

#### Launch artifacts (new, this prompt)
- [ ] `LAUNCH_HASHES_PRE.txt` — MD5 of locked files at start of compilation
- [ ] `LAUNCH_HASHES_POST.txt` — MD5 of locked files after compilation (must match PRE)
- [ ] `PAPER_TRADE_PRELAUNCH_CHECKLIST.md` (Section 4 of this doc — created by you)
- [ ] `MORNING_LAUNCH_RUNBOOK.md` (Section 5 of this doc — created by you)
- [ ] `EOD_REPORTING_TEMPLATE.md` (Section 6 — created by you)

**Total files = ~50. If even one is missing, paper trading is NOT ready.**

---

## 2. LOCKED FILES (DO NOT TOUCH UNDER ANY CIRCUMSTANCE)

These trading-logic files contain the strategy edge. Modifying any one of them = invalidates V1 baseline = paper trading is invalid.

```
live_options_trader.py
main_backtest.py
modules/strategy_mapper.py
modules/strategy_selector.py
modules/v3_utils.py
modules/candlestick_engine.py
modules/risk_guard.py
modules/regime/classifier.py
modules/confidence_scorer.py
modules/mean_reversion_engine.py
modules/momentum_engine.py
modules/context_detector.py
modules/indicator_engine.py
```

### Verification protocol

**At start of compilation:**
```python
import hashlib
LOCKED = [
    \"live_options_trader.py\", \"main_backtest.py\",
    \"modules/strategy_mapper.py\", \"modules/strategy_selector.py\",
    \"modules/v3_utils.py\", \"modules/candlestick_engine.py\",
    \"modules/risk_guard.py\", \"modules/regime/classifier.py\",
    \"modules/confidence_scorer.py\", \"modules/mean_reversion_engine.py\",
    \"modules/momentum_engine.py\", \"modules/context_detector.py\",
    \"modules/indicator_engine.py\",
]
with open(\"LAUNCH_HASHES_PRE.txt\", \"w\") as f:
    for fp in LOCKED:
        h = hashlib.md5(open(fp, \"rb\").read()).hexdigest()
        f.write(f\"{h}  {fp}\n\")
        print(f\"  {fp}: {h}\")
```

**At end of compilation:**
Re-run, save to `LAUNCH_HASHES_POST.txt`. Diff against PRE.

```bash
diff LAUNCH_HASHES_PRE.txt LAUNCH_HASHES_POST.txt
```

If output is non-empty → **immediately restore that file from operator's `audit_export.zip`** and re-verify. Do not proceed until diff is empty.

---

## 3. WRITABLE SURFACE (config files, your only editable territory)

You may read and write **only these files** during this session, and only via the API auto-backup mechanism:

```
config/*.yaml                           ← all 30 YAML configs
```

You may **NOT** edit:
- Anything under `modules/`
- Anything in the project root that ends in `.py`
- `.env` files (operator manages secrets)

Even within `config/*.yaml`, do not change strategy logic values like:
- `tp_atr`, `sl_atr` (R:R must stay 1.5/0.6 — matches V1 baseline)
- `min_confidence` thresholds (matches V1 baseline)
- Strategy enable/disable (operator's call, not yours)

Your config writes should be limited to: schema-validation, default population, and operator-driven changes coming from the frontend Save buttons. **Do not auto-tune.**

---

## 4. PAPER_TRADE_PRELAUNCH_CHECKLIST.md — what you must create

Create this file in the project root. It will be run by the operator at 21:00 IST tonight as the final go/no-go gate.

```markdown
# PAPER TRADE PRELAUNCH CHECKLIST
**Date:** <auto-fill with today's date>
**Capital:** ₹1,00,000 (Phase 25b — week 1 starter)
**Mode:** PAPER

## Step 1 — Codebase integrity
- [ ] Run: `python verify_v2.py preflight` (must print all PASS)
- [ ] Run: `diff LAUNCH_HASHES_PRE.txt LAUNCH_HASHES_POST.txt` (must be empty)
- [ ] Open `BACKEND_TO_UI_COMPLETENESS_ATTESTATION.md` — coverage must be 100%

## Step 2 — Backend services
- [ ] Backend starts: `cd AlgoTradingTelegramBotAndFrontend/backend && uvicorn server:app --port 8000`
- [ ] Health check: `curl http://localhost:8000/api/system/status` → 200 OK + JSON
- [ ] All 14 router endpoints respond:
    - [ ] GET /api/configs/list
    - [ ] GET /api/configs/risk_execution
    - [ ] GET /api/trades/live
    - [ ] GET /api/trades/history?from_date=...
    - [ ] GET /api/system/status
    - [ ] GET /api/logs/tail?lines=10
    - [ ] GET /api/docs/list
    - [ ] GET /api/strategies/list
    - [ ] GET /api/riskguard/state
    - [ ] GET /api/regime/current
    - [ ] GET /api/notifications/subscriptions
    - [ ] GET /api/backtest/history
    - [ ] WS /ws/live-pnl (connects, receives ping)
    - [ ] WS /ws/logs (connects, receives line)

## Step 3 — Frontend
- [ ] Frontend starts: `cd AlgoTradingTelegramBotAndFrontend/frontend && npm run dev`
- [ ] Open http://localhost:3000
- [ ] All 14 tabs render without console errors
- [ ] Each tab's Save button is visible (where applicable)
- [ ] Dashboard shows: capital, paper mode flag, system status, equity curve placeholder
- [ ] Configs tab can edit risk_execution.yaml + Save → check file on disk has new content
- [ ] Backtest tab can run a 1-day backtest end-to-end

## Step 4 — Live trader connectivity
- [ ] Click \"Start Live Trader\" from Dashboard
- [ ] Within 10 seconds, system_status shows \"live_trader_running: true\"
- [ ] Logs tab shows the live trader's boot lines
- [ ] Click \"Stop\" — process exits cleanly within 10 seconds

## Step 5 — Telegram (optional but recommended)
- [ ] Notifications tab → Send Test Message → Telegram receives it
- [ ] If failed: check .env has TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

## Step 6 — Capital and risk settings
- [ ] System Settings tab: TOTAL_CAPITAL = 100000 (NOT 500000 for week 1)
- [ ] System Settings tab: DAILY_LOSS_LIMIT_PCT = 0.025 (₹2,500 daily cap on ₹1L)
- [ ] System Settings tab: MAX_TRADES_PER_DAY = 4
- [ ] System Settings tab: MAX_CONSECUTIVE_LOSSES = 2
- [ ] Configs tab: PAPER_MODE = true (verify in .env too)

## Step 7 — Pre-trade simulation
- [ ] Backtest tab: run Nov 1, 2025 – Apr 30, 2026 with current config
- [ ] Expected: ~215 trades, ~51% win rate, +₹1.5L–₹2L net PnL
- [ ] If results differ by > 20% → STOP, do not launch live

## Step 8 — Market readiness
- [ ] Verify VIX feed: open http://localhost:8000/api/system/status → vix_value present
- [ ] Verify scrip master loaded: logs show \"scrip_master.initialize() OK\"
- [ ] Verify Angel One auth works: logs show \"broker connected\"
- [ ] Time is between 17:00 IST yesterday and 09:00 IST today

## Step 9 — Backups in place
- [ ] config/ has a backup taken today: `config/backups/<date>/`
- [ ] data/ has yesterday's paper_trades.jsonl preserved
- [ ] git status (if applicable) — uncommitted changes documented

## Step 10 — Operator sign-off
- [ ] Operator has reviewed expected daily P&L range: -₹2,500 to +₹3,500 typical
- [ ] Operator knows the kill switch: red button in Dashboard top-right
- [ ] Operator knows: if cumulative loss > ₹5,000 in week 1, STOP and reassess

## GO/NO-GO
If ALL 10 steps green → GO for tomorrow 09:15 launch.
If ANY step red → NO-GO. Fix and re-run.
```

---

## 5. MORNING_LAUNCH_RUNBOOK.md — what you must create

```markdown
# MORNING LAUNCH RUNBOOK — Phase 25b Day 1

## 09:00 IST — Pre-market boot
1. Open laptop, confirm internet stable
2. Terminal 1: `cd AlgoTradingTelegramBotAndFrontend/backend && uvicorn server:app --port 8000`
3. Terminal 2: `cd AlgoTradingTelegramBotAndFrontend/frontend && npm run dev`
4. Browser: open http://localhost:3000
5. Dashboard → System Status: confirm \"Backend: OK\", \"Broker: NOT CONNECTED\" (broker connects at 09:15)

## 09:14 IST — Final pre-trade check
1. Dashboard → click \"Start Live Trader\"
2. Watch Logs tab for boot sequence:
   - \"scrip_master initialized\"
   - \"broker connected\"
   - \"VIX feed live\"
   - \"📊 NIFTY AI Bot Started\"
   - \"Mode: PAPER\"
   - \"Capital: ₹100000\"
3. Telegram message arrives confirming bot start

## 09:15 IST — Market open
- DO NOT touch anything for the first 45 minutes
- SIGNAL_GATE=10:00 means no trades until 10:00 anyway
- Monitor Logs tab for any ERROR or WARNING

## 10:00 IST — Signal gate opens
- First trade may fire any time after this
- When a trade fires:
  - Live P&L tab shows the position card
  - Trades tab gets a new row
  - Telegram alert arrives
  - DO NOT manually intervene unless RiskGuard fails

## 12:00 IST — Hard cutoff
- NO new entries after this
- Existing positions managed to natural exit (SL / TP / EOD)

## 15:15 IST — Force close
- All positions auto-closed
- Day's PnL finalized
- EOD summary auto-pushed to Telegram

## 15:30 IST — Day done
1. Dashboard → click \"Stop Live Trader\"
2. Open EOD_REPORTING_TEMPLATE.md
3. Fill in today's data from Dashboard + Trades tab
4. Save as `eod_reports/day_1_<date>.md`

## Decision criteria after Day 1
- If today's PnL > +₹2,000 → continue with ₹1L next day
- If today's PnL between -₹2,500 and +₹2,000 → continue with ₹1L next day
- If today's PnL < -₹2,500 → SAFETY: RiskGuard tripped, review tomorrow with audit agent before re-launching

## Emergency procedures
- KILL SWITCH: Dashboard top-right red button. Immediately stops trader + closes all positions.
- Broker disconnect: Logs will show \"broker connection lost\". Bot auto-retries 3x. If still failed, stop and investigate.
- Internet down: Bot keeps running but cannot place trades. Wait for restoration. RiskGuard prevents bad trades.
```

---

## 6. EOD_REPORTING_TEMPLATE.md — what you must create

```markdown
# Day <N> EOD Report — <Date>

## Headline
- Capital start of day: ₹1,00,000
- Capital end of day:   ₹__________
- Net PnL today:        ₹__________  (___%)
- Trades placed:        __ / 4
- Wins / Losses:        __ / __
- Win rate today:       ___%

## Trades detail
| # | Time | Direction | Strike | Entry | Exit | PnL | Reason |
|---|------|-----------|--------|-------|------|-----|--------|
| 1 | ...  | CE        | 24500  | 102.5 | 108.2| +371 | TP |
| 2 | ...  | ...       | ...    | ...   | ...  | ... | ... |

## RiskGuard events
- Triggers today: __
- Consecutive losses: __
- Daily limit used: __% of ₹2,500 cap

## Anomalies / observations
- (free text)

## Tomorrow action
- [ ] Continue with same config
- [ ] Stop and reassess
- [ ] Escalate to audit agent
```

---

## 7. EXECUTION ORDER (do this exactly)

```
1.  Read this file (Section 0) and the 3 prior specs
2.  Run hash verification → save to LAUNCH_HASHES_PRE.txt
3.  Execute UNIFIED_DASHBOARD_INTEGRATION_SPEC.md (all backend routers + frontend tabs)
4.  Execute BACKEND_TO_UI_COMPLETENESS_AUDIT.md (all 7 phases)
5.  Create PAPER_TRADE_PRELAUNCH_CHECKLIST.md per Section 4 above
6.  Create MORNING_LAUNCH_RUNBOOK.md per Section 5 above
7.  Create EOD_REPORTING_TEMPLATE.md per Section 6 above
8.  Re-run hash verification → save to LAUNCH_HASHES_POST.txt
9.  diff PRE vs POST — must be empty
10. Self-test: open dashboard, navigate every tab, run a 1-day backtest, hit Save once
11. Write FINAL_COMPILATION_REPORT.md (Section 8 below)
12. Tell operator: ready for prelaunch checklist
```

---

## 8. FINAL_COMPILATION_REPORT.md — what you submit at the end

```markdown
# FINAL COMPILATION REPORT — <ISO timestamp>

## Files created
- Backend: __ new files
- Frontend: __ new files
- Audit artifacts: __ JSON files
- Launch artifacts: __ MD files
- **TOTAL: ___ files**

## Files modified
- AlgoTradingTelegramBotAndFrontend/backend/server.py (only `app.include_router()` lines added)
- config/<files modified via UI>

## Locked files unchanged
- All __ locked files MD5 verified: PRE == POST ✓

## Coverage stats (from BACKEND_TO_UI_COMPLETENESS_ATTESTATION.md)
- Backend elements: ___
- UI elements: ___
- Coverage: 100.00% ✓
- Gaps remaining: 0 ✓

## Self-test results
- Backend boots cleanly: ✓
- Frontend builds cleanly: ✓
- All 14 tabs render: ✓
- Save buttons functional: ✓
- 1-day backtest succeeded: ✓
- WebSockets connect: ✓
- Locked-file integrity: ✓

## Ready for paper trading
- [ ] Operator can run PAPER_TRADE_PRELAUNCH_CHECKLIST.md tonight
- [ ] Operator can follow MORNING_LAUNCH_RUNBOOK.md tomorrow 09:00 IST
- [ ] All systems green for ₹1L Phase 25b Day 1

## Blockers / known issues
(empty if all good — list any if not)
```

---

## 9. ABSOLUTE RULES

1. **Do not modify ANY locked file** (Section 2). Hash diff = automatic revert.
2. **Do not invent strategy parameters.** V1 baseline = the truth.
3. **Do not skip phases** from BACKEND_TO_UI_COMPLETENESS_AUDIT.md.
4. **Do not skip the 3-pass verifications** in Phases 4 and 6 of the audit.
5. **Do not produce summary metrics without underlying JSON files.**
6. **Do not modify capital from ₹1,00,000** for Phase 25b Day 1.
7. **Do not change PAPER_MODE from true.**
8. **Do not enable LIVE trading** under any pretext.
9. **If you hit a blocker, write `COMPILATION_BLOCKER.txt`** with: phase, error, suggested user action. Stop.
10. **The FINAL_COMPILATION_REPORT.md is a signed commitment.** Lying invalidates all of your prior work and ends the paper trade attempt.

---

## 10. ONE-LINE INSTRUCTION FOR THE OPERATOR TO PASTE

> *\"Read PHASE_25B_LAUNCH_PREP.md fully. Internalize Section 0 context. Execute Section 7 in order. Do not modify locked files. Produce all ~50 deliverable files. Submit FINAL_COMPILATION_REPORT.md when done. The operator launches paper trading tomorrow at 09:15 IST — your output must be ready by tonight.\"*

---

## 11. WHAT THE OPERATOR DOES TOMORROW MORNING (after your compilation)

Tomorrow 09:00 IST, with no further audit-agent involvement:
1. Open `PAPER_TRADE_PRELAUNCH_CHECKLIST.md`, work through Step 1-10
2. If GO → open `MORNING_LAUNCH_RUNBOOK.md`, work through 09:00-15:30 IST steps
3. At 15:30 IST → fill `EOD_REPORTING_TEMPLATE.md`
4. Day 2-5 → repeat with same checklist
5. After 5 sessions → escalate to audit agent for review before scaling capital

**Your job is to make tomorrow morning click-through-able for the operator. No hunting through code. No mid-launch debugging. No surprises.**

---

**END OF LAUNCH PREP. Build it. Ship it tonight. Paper trading starts tomorrow.**
"
Observation: Create successful: /app/PHASE_25B_LAUNCH_PREP.md