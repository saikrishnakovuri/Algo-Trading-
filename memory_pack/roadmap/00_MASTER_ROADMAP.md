# 00 — MASTER ROADMAP
## 📊 Project Reality Check
Current state: Phase 24d backtest baseline PASS (₹385K/6M, 7% DD, OOS PF 1.46) **BUT** the audit revealed 8 P0 bugs that invalidate this baseline. Plus user has 73 new requirements spanning:
- Live tick-streaming TradingView-style charts
- Real NIFTY options integration (no synthetic prices)
- 1000-1500 stock monitoring dashboard
- V2 hybrid AI+human discretionary platform
- Eventual conversion to "Sai Krishna's Indicator"
This is **months of work**, not days. Sequencing matters.
## 🚦 Critical Sequencing Rules
**RULE 1**: Cannot go live until Phase 25a (P0 audit fixes) complete + Phase 26 (paper trade infrastructure) verified.
**RULE 2**: Cannot build V2 chart (Phase 29) until live data backbone (Phase 26) works.
**RULE 3**: Cannot run "Sai Krishna's Indicator" (Phase 30) until everything else works AND has been live for 2+ weeks.
**RULE 4**: User's "May 13-15 observation window" requirements (items 26, 32, 36, 37) belong to Phase 26 (Forced Observation Mode).
## 📁 Phase MD Files (read in order)
| # | File | Phase | Time est. | Dependency |
|---|---|---|---|---|
| 1 | `01_PHASE_25a_P0_FIXES.md` | 25a — Audit P0 cleanup | 2-3 days | Audit report |
| 2 | `02_PHASE_26_LIVE_BACKBONE.md` | 26 — Live trading backbone + observation mode | 4-5 days | 25a |
| 3 | `03_PHASE_27_NIFTY_OPTIONS_LIVE.md` | 27 — Real option chain integration | 3-4 days | 26 |
| 4 | `04_PHASE_28_STOCKS_DASHBOARD.md` | 28 — Stocks monitoring tab (parallel) | 2-3 days | Can run parallel to 27 |
| 5 | `05_PHASE_29_V2_DASHBOARD_CHART.md` | 29 — V2 dashboard + live chart + AI feedback | 7-10 days | 26, 27 |
| 6 | `06_PHASE_30_INDICATOR_PRODUCT.md` | 30 — Convert to indicator product | 5-7 days | All above stable for 2+ wks |
## ⛔ Hard Gates Between Phases
```
Phase 25a PASS  ─►  Phase 26 starts
Phase 26 PASS   ─►  Phase 27 + 28 (parallel)
Phase 27 PASS   ─►  Phase 29 starts (28 can be in progress)
Phase 29 PASS   ─►  2 weeks live observation ─► Phase 30
```
NO phase can begin if its dependency is in FAIL state. NO live capital deployment until BOTH Phase 26 paper trade passes AND Phase 27 real options data is verified for 5 trading days.
## 🎯 Phase Acceptance Gate Format
Each phase file has 3 mandatory sections:
1. **Requirements** — Numbered from user's needs document
2. **Tests** — Surgical, automatable, deterministic
3. **Expected Output** — What "PASS" looks like
4. **Acceptance Gate** — Boolean: ALL pass → next phase. ANY fail → fix and retest.
Gemini (or your local executor) must report each test's PASS/FAIL status verbatim to the architect. The architect (next AI) decides go/no-go based on the gate criteria — no waivers.
## 💸 Credit-Budget Awareness (for the human pilot)
Your Emergent credits should be reserved for:
- Phase 25a planning (already done in this conversation)
- Mid-phase debugging when Gemini gets stuck (1 architect consultation per phase blocker)
- Final review before live deployment
Routine file edits, test runs, and small fixes → use Gemini/Cursor/Claude Code locally.
## 🗂 Where the existing memory_pack files fit
The 6 existing `memory_pack/0X_*.md` files describe **what already exists** (Phase 1-24d). The 6 new phase files in this folder describe **what to build next** (Phase 25a-30). Both are needed.
When handing off to a new model, the new model should read:
1. `memory_pack/01_project_overview.md` → `06_current_state_and_next_steps.md` (history)
2. `memory_pack/AUDIT_REPORT_pre_paper_trade.md` (open bugs)
3. `roadmap/00_MASTER_ROADMAP.md` → `06_PHASE_30_INDICATOR_PRODUCT.md` (forward plan)
## 🚨 What the User MUST Do First
1. Read all 6 phase files
2. Confirm capital tier: ₹500K vs ₹1M vs other
3. Confirm Angel One SmartAPI supports: WebSocket streaming + option chain + India VIX
4. Decide May 13-15 testing window dates (or any other 3-day observation window)
5. Set up local Git repo with checkpoint discipline (commit before every phase)
## ⚠️ Reality on Timeline
- User asked for "7-day stabilization goal" (item 72). The actual scope of items 1-73 is **6-10 weeks** of full-time work.
- Item 72's 7-day goal can be achieved IF scope is reduced to: Phase 25a + Phase 26 only. That's enough to go live with the EXISTING strategy on EXISTING NIFTY/BANKNIFTY data, with stability and observation mode.
- V2 chart, real options integration, stocks dashboard, indicator product → all WEEKS of work each. Don't rush them.
- Set honest expectation: **Sai Krishna's Indicator (Phase 30) is a Q2-Q3 2026 goal, not "this week".**
