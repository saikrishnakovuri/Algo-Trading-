# OPUS Agent Review Guide

Purpose: a focused, actionable guide for an automated reviewer (Opus) to audit this repo. It lists the main engines, key files to review, likely bug hotspots, secrets to flag, and a concise review checklist.

---

## 1 — Quick instructions for the Opus agent

- Scope the review to correctness, safety (live trading), reproducibility, performance, and configuration.
- Prioritize: (1) live-trading safety & secrets, (2) core engine correctness (`backtest_engine.py`), (3) data pipeline integrity (`data/`), (4) config drift and YAML validation, (5) tests and CI.
- Deliverables: prioritized issue list (severity + file), suggested quick fixes (with minimal patches), and test suggestions.

---

## 2 — Code conduct & review checklist

- **Secrets & credentials:** Find `.env`, `broker_tokens.json`, `broker_tokens_full.json`, and any hard-coded keys. Flag and recommend moving to secure vaults.
- **Safety checks (live):** Ensure dry-run modes, rate-limit handling, order size guards, emergency-exit, and idempotent order submission.
- **Data correctness:** Validate time-index alignment, timezone handling, missing/NaN handling, and consistent sorting/uniqueness of timestamps.
- **Reproducibility:** Confirm `requirements.txt`, pinned dependencies, deterministic seeds, and clear data cache policies.
- **Error handling:** Check for unhandled exceptions in API calls and background threads.
- **Concurrency & locking:** Inspect `utils/pid_lock.py`, scheduler code, and any shared-file writes for race conditions.
- **Performance:** Look for hot loops in `backtest_engine.py`, heavy IO in inner loops, and opportunities to batch work.
- **Testing:** Confirm unit tests cover core engines (`tests/`), and flag missing tests for critical logic (P&L, slippage, execution).
- **Logging & observability:** Ensure structured logs, meaningful error messages, and proper log rotation.

---

## 3 — Project map: main engines & important files to hand to Opus

Below are the top-priority files and why they matter. Provide these to the Opus agent for an initial review pass.

### Core backtesting & simulation
- `backtest_engine.py` — Core backtest loop and execution model. Verify P&L math, trade lifecycle, slippage and fees, and time-alignment.
- `backtest_engine_v1.py` — Legacy variant; compare behavior and divergence from the main engine.
- `main_backtest.py`, `main.py` — Entrypoints that wire config into engines; verify argument parsing and config usage.
- `run_backtest.py`, `run_complete_backtest_system.py`, `run_combined_backtest.py` — Batch runners and orchestration scripts.

### Optimization & analysis
- `master_optimizer.py` — Parameter search / optimizer. Check checkpointing, parallelism, and reproducibility of runs.
- `walk_forward_optimizer.py`, `walk_forward.py` — Walk-forward logic and cost accounting.

### Live trading & exchange integration (HIGH RISK)
- `optimized_gemini_client.py`, `debug_gemini_api.py` — Exchange API wrapper; check retry logic, rate limits, and credential handling.
- `live_trader_v1.py`, `live_trader_v2.py`, `live_trader_v3.py` — Live-trading processes; verify safety gates (max position, dry-run flags), order idempotency, and error recovery.
- `live_options_trader.py` — Options-specific live logic and margin/size checks.
- `live_trader_crypto.py` — Crypto-specific differences and exchange behavior.
- `live_dry_run.py` — Dry-run harness—ensure parity with live logic.
- `overnight_scheduler.py`, `orchestrator.py` — Scheduling & coordination; check job overlap protections.

### Data, caching & persistence
- `data/` directory (all) — Cached market data, composite features, and precomputed results. Validate data lineage, schema, and freshness rules.
- `meta_db*.json`, `meta_config.json` — Metadata stores driving universes and parameters.

### Configuration
- `config/*.yaml` (e.g., `strategy_filter.yaml`, `momentum.yaml`, `mean_reversion.yaml`, `portfolio_limits.yaml`) — Strategy and risk configurations. Validate schema and allowed ranges; detect mismatches between YAML and code defaults.

### Utilities & infra
- `utils/logger.py` — Central logging utilities.
- `utils/pid_lock.py` — Single-instance guard; ensure robust cleanup on crashes.
- `orchestrator.py` — High-level process coordinator.

### Scripts & pipelines
- `scripts/*` — Large collection: backtest pipelines, generation scripts, validation and profiling tools (e.g., `generate_universe.py`, `comprehensive_backtest.py`, `validation_*`). These are useful for integration tests and reproducing analyses.

### Price-action & alternate engines
- `Priceactionmdfiles/optimized_backtest.py`, `Priceactionmdfiles/*` — Additional engine implementations and research notebooks.

### Tests & dashboard
- `tests/` — Unit tests and test suites (e.g., `tests/test_vp_avwap/`, `test_phase_13_diagnostics.py`). Run and report failing tests first.
- `dashboard/app.py`, `dashboard/charts.py` — Dashboard backend; check API endpoints and data exposure.

### Packaging & environment
- `requirements.txt` — Pin dependencies; recommend confirming exact versions and running `pip check`.
- `.env` and `.env.example` — Environment variables; ensure secrets are not committed.

---

## 4 — Bug hotspots & common failure modes (prioritized)

1. Data alignment and timezone bugs (leading to lookahead / leakage).
2. Execution model vs. market simulation mismatch (slippage, fees, partial fills).
3. Live-trading error handling: uncaught API errors, retry storms, and order duplication.
4. Race conditions around PID locks, scheduler overlaps, and file/DB writes.
5. Configuration drift: YAML values not validated, resulting in unsafe live params.
6. Secrets accidentally committed (`broker_tokens.json`, `.env`).
7. Missing or flaky tests for numerical edge cases (zero volume, NaN prices).
8. Long-running scripts that mutate shared caches without transactional safety.

---

## 5 — Files to hand to Opus (recommended subset)

Group A — Engines & orchestration (highest priority):
- `backtest_engine.py`
- `orchestrator.py`
- `master_optimizer.py`
- `main_backtest.py`
- `run_backtest.py`

Group B — Live trading (safety-critical):
- `optimized_gemini_client.py`
- `live_trader_v1.py`
- `live_trader_v2.py`
- `live_trader_v3.py`
- `live_options_trader.py`
- `live_dry_run.py`

Group C — Data & config:
- `data/` (top-level folder summary file or subset)
- `config/*.yaml`
- `meta_db*.json`

Group D — Utilities & tests:
- `utils/logger.py`
- `utils/pid_lock.py`
- `tests/` (all)
- `requirements.txt`

Group E — Sensitive & attention-required files (flag and exclude from public audits):
- `.env` (exists at repo root)
- `broker_tokens.json`
- `broker_tokens_full.json`

---

## 6 — Concrete review tasks for Opus (checklist items to perform)

1. Static analysis: run a linter and flag cyclomatic complexity hotspots.
2. Secrets scan: search for `token|api_key|broker|secret|password` across repo.
3. Run unit tests: `pytest tests/` and report failures.
4. Smoke-run `backtest_engine` on a tiny dataset; compare outputs against golden files in `data/backtest_results`.
5. Audit live-trading code paths: ensure dry-run mode, order guards, and emergency-stop hooks are present.
6. Report missing tests for any public function in engines.

---

## 7 — Quick commands (PowerShell) to run locally

```powershell
# create venv and install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# run tests
pytest tests -q

# scan for obvious secrets (case-insensitive)
Select-String -Path "**\*" -Pattern 'token|secret|api_key|password|broker' -SimpleMatch -CaseSensitive:$false
```

---

## 8 — Expected Opus report format

- **Summary:** 3–5 high-severity issues (safety/security/performance) with file references.
- **Detailed findings:** for each file, explain the issue, example failing lines (or minimal repro), and suggested patch.
- **Tests:** list failing tests with stack traces, and suggest focused unit tests to add.
- **Priority fixes:** small, high-impact patches (e.g., add dry-run guard, wrap API calls with retries, remove committed secrets).

---

## 9 — Next steps I can take for you

- Run a secrets scan and produce a list of flagged files.
- Run `pytest` and share failing tests and tracebacks.
- Run a lightweight static analysis (`ruff` or `flake8`) and list issues.

If you want me to proceed with any of these, tell me which one to run first.

---

*File generated: `OPUS_AGENT_REVIEW.md` — created to guide an automated Opus review and manual audits.*
