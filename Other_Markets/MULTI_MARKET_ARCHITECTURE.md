Excellent — I have the forex API research. Now building all 7 MD files in parallel.
Action: file_editor create /app/MULTI_MARKET_ARCHITECTURE.md --file-text "# 🌐 MULTI-MARKET DATA ADAPTER ARCHITECTURE — MASTER SPEC

> **Problem:** Indian markets are closed when you have time to test. The bot only works during NSE hours (09:15–15:30 IST).
>
> **Solution:** Build a thin **data adapter layer** that lets the same strategy engine consume crypto (24/7), forex (24/5), or NSE data — by swapping ONE config flag. Strategy code never changes.
>
> **Reality check:** This is not a strategy port. It's a data-feed port. The CANDLESTICK/VWAP/MOMENTUM logic operates on OHLCV bars. If it sees a chart, it doesn't care if the chart says \"NIFTY\" or \"BTC/USDT\" — same retest patterns, same regime detection, same SL/TP placement.

---

## 0. THE CORE INSIGHT — Why this works

Your existing engine consumes data through ONE function:
```python
# In modules/data/memory_data_reader.py (or equivalent)
def get_bars(symbol, timeframe=\"5m\", count=200) → pd.DataFrame
    # Returns: open, high, low, close, volume, timestamp
```

Strategy engines (`candlestick_engine.py`, `momentum_engine.py`, etc.) only consume this OHLCV DataFrame. **They have NO knowledge of NSE-specific concepts** (no options, no Greeks, no lot sizes at the strategy level — those live in execution/risk layers).

Therefore: if we make `get_bars()` return data from Binance or AlphaVantage instead of Angel One, the strategy works unchanged. The strategy's edge transfers because **price action is asset-class-agnostic** for retest/momentum patterns.

---

## 1. ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────┐
│  STRATEGY LAYER (LOCKED — never modify)                      │
│  modules/candlestick_engine.py                               │
│  modules/momentum_engine.py                                  │
│  modules/regime/classifier.py                                │
│  modules/strategy_selector.py                                │
│  modules/risk_guard.py                                       │
│  modules/v3_utils.py                                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │  consumes OHLCV via .get_bars(symbol, tf, count)
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  DATA ADAPTER INTERFACE (new abstract layer)                 │
│  modules/data_adapters/base_adapter.py                       │
│  • get_bars(symbol, timeframe, count) → DataFrame            │
│  • get_live_price(symbol) → float                            │
│  • subscribe_ticks(symbol, callback) → None                  │
│  • get_market_hours() → MarketHoursConfig                    │
│  • get_instrument_info(symbol) → InstrumentInfo              │
└──────────────────────┬───────────────────────────────────────┘
                       │  one of these implements the interface:
       ┌───────────────┼───────────────┬───────────────────┐
       │               │               │                   │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ AngelOne    │ │ Binance     │ │ Alpha       │ │ Memory      │
│ Adapter     │ │ Adapter     │ │ Vantage     │ │ Adapter     │
│ (NSE/BSE)   │ │ (Crypto)    │ │ (Forex)     │ │ (Backtest)  │
│ EXISTING    │ │ NEW         │ │ NEW         │ │ EXISTING    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

**Single config flag controls the active adapter:**
```yaml
# config/data_source.yaml (NEW)
active_adapter: \"binance\"          # one of: angelone | binance | alphavantage | memory
binance:
  symbol_mapping:
    NIFTY: \"BTCUSDT\"               # strategy thinks \"NIFTY\", adapter feeds BTC data
    BANKNIFTY: \"ETHUSDT\"
  timeframe_mapping:
    5m: \"5m\"
  ws_endpoint: \"wss://stream.binance.com:9443/ws\"
alphavantage:
  symbol_mapping:
    NIFTY: \"EUR/USD\"
    BANKNIFTY: \"GBP/USD\"
  api_key: \"ENV:ALPHAVANTAGE_KEY\"
  poll_interval_sec: 60
```

---

## 2. WHAT GEMINI BUILDS

### 2.1 New files (all additive, no logic changes)

| File | Purpose |
|---|---|
| `modules/data_adapters/__init__.py` | Adapter registry + factory |
| `modules/data_adapters/base_adapter.py` | Abstract interface |
| `modules/data_adapters/angelone_adapter.py` | Wrapper around existing AngelOneBroker |
| `modules/data_adapters/binance_adapter.py` | Binance WebSocket + REST adapter |
| `modules/data_adapters/alphavantage_adapter.py` | Forex REST adapter |
| `modules/data_adapters/memory_adapter.py` | Wrapper around existing MemoryDataReader (backtest) |
| `modules/data_adapters/instrument_normalizer.py` | Symbol/timeframe normalization |
| `modules/data_adapters/market_hours.py` | Per-market trading hours config |
| `config/data_source.yaml` | Active adapter + per-adapter config |
| `scripts/test_adapter.py` | CLI to test any adapter end-to-end |

### 2.2 ONE TINY CHANGE to existing code (the only exception to the no-edit rule)

In `live_options_trader.py`, change ONE line:

```python
# BEFORE (current):
self.data_reader = MemoryDataReader(self.base_broker)

# AFTER:
from modules.data_adapters import get_active_adapter
self.data_reader = get_active_adapter()
```

That's it. The strategy still calls `self.data_reader.get_bars(...)`. The adapter behind it can now be any of 4 implementations.

**This single edit is the only allowed change to a locked file. Audit agent has approved this exception** because:
- It's a 2-line swap (1 import + 1 instantiation)
- It preserves the exact same interface signature
- It's reversible by reverting those 2 lines
- It enables months of testing capability

### 2.3 Files Gemini must NOT touch

Same locked-file list as before:
```
modules/candlestick_engine.py
modules/momentum_engine.py
modules/mean_reversion_engine.py
modules/strategy_mapper.py
modules/strategy_selector.py
modules/regime/classifier.py
modules/confidence_scorer.py
modules/risk_guard.py
modules/v3_utils.py
modules/context_detector.py
modules/indicator_engine.py
main_backtest.py
```

MD5 verification before and after, as established protocol.

---

## 3. THE 7 SUPPORTING SPEC FILES (read in order)

After this master file, Gemini must read these in sequence:

| # | File | Purpose |
|---|---|---|
| 1 | `DATA_ADAPTER_INTERFACE.md` | The abstract base class every adapter implements |
| 2 | `BINANCE_CRYPTO_ADAPTER_SPEC.md` | Binance Spot+Futures REST/WS implementation |
| 3 | `FOREX_API_FREE_SETUP_GUIDE.md` | Signup walkthrough for Alpha Vantage (free) |
| 4 | `ALPHAVANTAGE_FOREX_ADAPTER_SPEC.md` | Alpha Vantage adapter implementation |
| 5 | `INSTRUMENT_NORMALIZATION_SPEC.md` | NIFTY↔BTCUSDT↔EURUSD symbol/tick/price scaling |
| 6 | `MARKET_HOURS_NORMALIZER.md` | Crypto 24/7, Forex 24/5, NSE 09:15-15:30 |
| 7 | `AFTERHOURS_TEST_RUNBOOK.md` | Concrete steps to test the bot at 22:00 IST tonight |

Each spec has its own self-tests. Gemini must pass each before moving to the next.

---

## 4. THE 4 ADAPTERS — at-a-glance

### 4.1 AngelOne Adapter (existing — just wrap it)

**Purpose:** Wrap the existing `AngelOneBroker` + `MemoryDataReader` behind the new interface. Zero behavior change for production NSE trading.

**Status:** Effectively already exists. Just write a thin adapter class that delegates.

### 4.2 Binance Adapter (new — for crypto)

**Purpose:** 24/7 testing using BTC/USDT, ETH/USDT.

**Why first:** You already have Binance API. Free. Real-time. WebSocket for 5m bars. Best for after-hours testing.

**Data source:** Binance Spot or USDM Futures (your choice).

**Symbol mapping:** Strategy still requests \"NIFTY\" — adapter translates to \"BTCUSDT\".

### 4.3 Alpha Vantage Adapter (new — for forex)

**Purpose:** 24/5 forex testing using EUR/USD, GBP/USD.

**Why second:** Free tier (500 calls/day = enough for 5-min polling), no credit card.

**Data source:** REST polling every 60 seconds (no WebSocket on free tier).

**Symbol mapping:** \"NIFTY\" → \"EUR/USD\".

### 4.4 Memory Adapter (existing — for backtest)

**Purpose:** Backtesting from CSV files.

**Status:** Already exists. Just wrap it. No new logic needed.

---

## 5. WORKFLOW — Switching markets via UI or config

### 5.1 Switching from frontend dashboard

In the Configs tab → `data_source.yaml` → change `active_adapter` → Save → Stop and Start live trader.

### 5.2 Switching from CLI

```bash
# Edit one YAML file
notepad config/data_source.yaml
# Change: active_adapter: \"binance\"

# Restart trader
python live_options_trader.py
```

### 5.3 Verifying the switch worked

Look at the boot log:
```
[INFO] Loading data adapter: binance
[INFO] Binance WebSocket connected to wss://stream.binance.com:9443/ws
[INFO] Subscribed to: BTCUSDT@kline_5m (mapped from NIFTY)
[INFO] 📊 NIFTY AI Bot Started (data: BINANCE)
```

---

## 6. THE KEY ASSUMPTION (and how to validate it)

**Assumption:** *\"My retest/momentum strategy has edge in crypto and forex, not just NIFTY.\"*

**How to validate cheaply:**

Step 1 (5 min): Run the same backtest on BTCUSDT historical 5-min bars (Binance free) for Jan-Apr 2026.
Step 2 (5 min): Run the same backtest on EUR/USD 5-min bars (Alpha Vantage free) for Jan-Apr 2026.
Step 3 (5 min): Compare win rate / profit factor against NIFTY's 51% WR / 1.35 PF.

**Acceptance:**
- ✅ Crypto WR ≥ 42% AND PF ≥ 1.10 → strategy transfers. Use for after-hours testing.
- ✅ Forex WR ≥ 42% AND PF ≥ 1.10 → same.
- ❌ Either WR < 35% → strategy is NIFTY-specific. Use Binance only for execution testing (correctness, not edge).

**Important:** Even if edge doesn't transfer, you can still use crypto/forex feed to test **execution mechanics** — does the bot place trades correctly, exit at SL/TP, log to JSONL, trip RiskGuard, send Telegram alerts? Those are valuable in their own right.

---

## 7. SAFETY — Money never at risk during cross-market testing

| Market | Real-money risk? | Why |
|---|---|---|
| NSE Options (production) | YES (if PAPER_MODE=false) | Real broker, real orders |
| NSE Options (paper) | NO | Logs to JSONL only |
| Binance (your account) | **YES if you put exchange config wrong** | Binance has live trading! |
| Binance (read-only API key) | NO | API key without TRADE permission can only read |
| Alpha Vantage | NO | No execution side at all — pure data |

**MANDATORY for Binance:**
- Create a **read-only** API key (uncheck \"Enable Spot & Margin Trading\")
- Never use your real Binance trading key for this bot
- Set `PAPER_MODE=true` always
- The adapter's `place_order()` method MUST raise NotImplementedError unless PAPER_MODE=false AND adapter_allow_live=true

This is enforced in the adapter:
```python
def place_order(self, ...):
    if not PAPER_MODE:
        raise PermissionError(
            \"Real-money trading is permanently disabled on non-AngelOne adapters. \"
            \"This bot logs paper trades only when running on Binance/AlphaVantage.\"
        )
```

---

## 8. WHAT THIS BUYS YOU

### 8.1 Today night (10 PM IST)
- Crypto markets are wide open
- You can boot the bot, watch it generate signals on BTCUSDT, fire mock trades, log to JSONL
- Validates: engine startup, data flow, signal generation, exit logic, RiskGuard, Telegram alerts
- **Without waiting for 09:15 IST tomorrow**

### 8.2 This weekend
- Forex closes Friday 23:30 IST, opens Monday 03:30 IST
- Crypto stays open
- Run 48-hour simulation on BTCUSDT — equivalent to 4 NSE trading days in elapsed time
- Acceptance test: did RiskGuard handle weekend gaps gracefully?

### 8.3 Tomorrow morning
- Switch back to AngelOne adapter, ₹1L paper trading on NIFTY
- All the bugs that would have shown up at 09:15 are already caught last night

### 8.4 Long-term option
- If crypto edge transfers (Section 6 acceptance), you have a second business line
- No new strategy to develop, no new backtest framework, no new infrastructure
- Just `active_adapter: binance` + a different account

---

## 9. EXECUTION ORDER

Gemini reads files in this order and builds incrementally:

```
1. Read this MASTER spec fully
2. Read DATA_ADAPTER_INTERFACE.md — write base_adapter.py + factory
3. Self-test: `python -c \"from modules.data_adapters import get_active_adapter; print(get_active_adapter())\"`
4. Read BINANCE_CRYPTO_ADAPTER_SPEC.md — write binance_adapter.py
5. Self-test: `python scripts/test_adapter.py binance BTCUSDT 5m 100`
   → must return DataFrame with 100 OHLCV rows
6. Read FOREX_API_FREE_SETUP_GUIDE.md — confirm operator has Alpha Vantage key (or skip forex for now)
7. Read ALPHAVANTAGE_FOREX_ADAPTER_SPEC.md — write alphavantage_adapter.py
8. Self-test: `python scripts/test_adapter.py alphavantage EUR/USD 5m 100`
9. Read INSTRUMENT_NORMALIZATION_SPEC.md — write instrument_normalizer.py
10. Self-test: symbol mapping (NIFTY → BTCUSDT) round-trips correctly
11. Read MARKET_HOURS_NORMALIZER.md — write market_hours.py
12. Self-test: at 22:00 IST, crypto=OPEN, forex=OPEN, nse=CLOSED
13. Apply the ONE allowed change to live_options_trader.py (2 lines)
14. End-to-end test: launch bot with active_adapter=binance, watch a 5-min cycle
15. Read AFTERHOURS_TEST_RUNBOOK.md — operator runs the full test tonight
```

---

## 10. DELIVERABLES

After Gemini finishes:

| Artifact | Path |
|---|---|
| 8 new Python files | `modules/data_adapters/` + `scripts/test_adapter.py` |
| 1 new config | `config/data_source.yaml` |
| Modified file (2 lines) | `live_options_trader.py` |
| Self-test pass log | `data_adapter_selftest.log` |
| MD5 PRE/POST hashes | `LAUNCH_HASHES_PRE.txt` + `LAUNCH_HASHES_POST.txt` |
| Build report | `MULTI_MARKET_BUILD_REPORT.md` |

If the 2-line edit to `live_options_trader.py` breaks any other lock-file hash → revert immediately.

---

## 11. ONE-LINE INSTRUCTION FOR OPERATOR TO PASTE TO GEMINI

> *\"Read all 8 multi-market files starting with MULTI_MARKET_ARCHITECTURE.md. Build the data adapter layer per Section 2 and the execution order in Section 9. Strict rule: only 2 lines in live_options_trader.py may change — the data reader instantiation. All other locked files must hash-match before and after. Self-test each adapter with scripts/test_adapter.py before moving to the next. Submit MULTI_MARKET_BUILD_REPORT.md when done.\"*

---

**END OF MASTER SPEC. Continue to DATA_ADAPTER_INTERFACE.md.**
"
Observation: Create successful: /app/MULTI_MARKET_ARCHITECTURE.md