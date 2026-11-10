
Action: file_editor create /app/AFTERHOURS_TEST_RUNBOOK.md --file-text "# 🌙 AFTER-HOURS TEST RUNBOOK — Test the Bot Tonight Without NSE

> Concrete, click-by-click guide. Run from 22:00 IST tonight onward. Validates the entire pipeline before tomorrow's NSE paper trading.

---

## 1. PRE-REQUISITES (do BEFORE 22:00 IST)

- [ ] Gemini has built all 7 multi-market adapter files (per MULTI_MARKET_ARCHITECTURE.md)
- [ ] `scripts/test_adapter.py binance BTCUSDT 5m 100` passes (~50 trades simulated)
- [ ] `config/data_source.yaml` exists and is readable
- [ ] `.env` has `BINANCE_API_KEY` (optional, public data works without)
- [ ] `.env` has `PAPER_MODE=true` (mandatory)
- [ ] Dashboard from `UNIFIED_DASHBOARD_INTEGRATION_SPEC.md` is running
- [ ] `LAUNCH_HASHES_PRE.txt` and `_POST.txt` match (locked files unchanged)

If any item is unchecked → fix before proceeding.

---

## 2. TEST PHASE 1 — DRY-RUN ADAPTER VALIDATION (10 min)

Goal: confirm Binance adapter is working before exposing the bot to it.

### Step 1.1 — Set adapter to Binance
```powershell
cd \"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\"
notepad config\data_source.yaml
# Set: active_adapter: \"binance\"
# Save and close
```

### Step 1.2 — Run adapter CLI test
```powershell
python scripts\test_adapter.py binance BTCUSDT 5m 200
```

Expected output (key lines):
- `[TEST] Adapter loaded: <BinanceAdapter ...>`
- `[TEST] Returned 200 bars`
- A table showing OHLCV bars with BTC prices ~104,000-106,000 range
- `[TEST] ✅ All assertions passed.`

If you see this → adapter works. Proceed.

If you see errors:
- `Binance REST unreachable` → check internet, try again
- `Symbol not found` → check `data_source.yaml` symbol_mapping
- `ATR sanity check failed` → adapter has a unit bug, report to me

### Step 1.3 — Strategy-side symbol test
```powershell
python -c \"from modules.data_adapters import get_active_adapter; a=get_active_adapter(); print(a.get_live_price('NIFTY')); print(a.get_bars('NIFTY','5m',5))\"
```

Expected: BTC price (~105,000) and 5 recent bars when called with \"NIFTY\" — confirms symbol mapping works.

---

## 3. TEST PHASE 2 — DASHBOARD HEALTH CHECK (5 min)

### Step 2.1 — Start dashboard backend + frontend
```powershell
# Terminal 1:
cd AlgoTradingTelegramBotAndFrontend\backend
.\venv\Scripts\activate
uvicorn server:app --port 8000

# Terminal 2:
cd ..\frontend
npm run dev
```

### Step 2.2 — Open http://localhost:3000

### Step 2.3 — Verify on Dashboard tab:
- [ ] System Status shows: `Active Adapter: BINANCE`
- [ ] Market Status shows: `🟢 OPEN (crypto 24/7)`
- [ ] Current Symbol: `BTCUSDT` (mapped from NIFTY)
- [ ] Live Price ticker updates within 30 seconds

### Step 2.4 — Visit Logs tab
- [ ] No `ERROR` lines from adapter initialization
- [ ] You should see: `[BinanceAdapter] REST ping OK (XXms)`

If any check fails → STOP, report to me with screenshot.

---

## 4. TEST PHASE 3 — DRY-RUN LIVE TRADER (15 min)

Goal: actually start the trading loop, watch signals fire, verify execution flow.

### Step 3.1 — Adjust v3_utils for testing (optional, makes signals fire faster)

Edit `v3_utils.py` ONLY to relax time gates for this test:
```python
# TEMPORARY for after-hours test — REVERT BEFORE NSE LAUNCH
SIGNAL_GATE = \"00:00\"        # was \"10:00\"
NO_ENTRY_AFTER = \"23:59\"     # was \"12:00\"
FORCE_CLOSE_AT = \"23:59\"     # was \"15:15\"
```

**Wait — this violates locked-file rule.** Better approach:

Don't edit v3_utils.py. Instead, have Gemini implement `OVERRIDE_TIME_GATES_FOR_TEST` env variable:
```bash
# In .env (temporary, just for this test)
OVERRIDE_TIME_GATES_FOR_TEST=true
```

The live_options_trader.py 2-line allowed edit can include reading this env var. **Confirm with Gemini that this env override is implemented.**

If not implemented and you need quick test: revert to using the existing `09:45 → 12:00` window, and run the test during those IST hours of the next forex day. Or simply wait until tomorrow 10:00 IST and use BTC data for the first session as a dry run before switching back to NIFTY.

### Step 3.2 — Start live trader from Dashboard
- Click **\"Start Live Trader\"** button
- Watch the Logs tab streaming

Expected boot sequence within 30 seconds:
```
[INFO] Loading data adapter: binance
[INFO] BinanceAdapter REST ping OK
[INFO] Subscribed to BTCUSDT@kline_5m
[INFO] RiskGuard initialized: capital=₹100000
[INFO] StrategySelector ready
[INFO] 📊 NIFTY AI Bot Started (data: BINANCE, mode: PAPER)
[INFO] Telegram boot message sent
```

If you have Telegram set up, you receive: `🚀 NIFTY AI Bot Started — Mode: PAPER — Capital: ₹100000 — Adapter: BINANCE`

### Step 3.3 — Watch for first signal

Crypto is volatile, so signals should fire within 30-60 minutes during active hours. Possible signal events:

```
[INFO] [BTCUSDT] Regime: TRENDING_UP
[INFO] [BTCUSDT] Candidate: CANDLESTICK score=58 threshold=55 PASS
[INFO] [SIGNAL] BUY BTCUSDT @ 105,234 SL=105,180 TP=105,381
[INFO] [PAPER-FILL] Lot=1 filled at 105,234 (no real order placed)
[INFO] Telegram alert: 📈 BUY NIFTY... (mapped from BTCUSDT)
```

### Step 3.4 — Verify on dashboard

- **Trades tab**: new row appears with the simulated trade
- **Live P&L tab**: position card shows live LTP + unrealized PnL
- **Telegram**: trade alert message received

### Step 3.5 — Wait for exit

Watch the trade exit. Possible outcomes:
- **TP hit**: green +PnL trade
- **SL hit**: red −PnL trade
- **Time exit** (if you waited past force_close_at): EOD exit

### Step 3.6 — Verify EOD logging

Open `data/paper_trades.jsonl` in Notepad. The latest line should be the closed trade with full details.

---

## 5. TEST PHASE 4 — STRESS TEST (overnight optional)

If steps 1-3 pass, you can leave the bot running overnight on Binance. By morning:
- 8-10 hours of operation = 5-15 trades simulated
- Telegram receives EOD summary at force_close_at
- RiskGuard state in `data/risk_guard_state.json` should look correct

### Things to check the next morning:

1. **No crashes** — open Logs tab, scroll to oldest, verify no unhandled exceptions
2. **No silent failures** — every signal that fired should have a corresponding trade row in `paper_trades.jsonl`
3. **RiskGuard fired at limits** — if losses exceeded ₹2,500 in a session, RiskGuard should have stopped trading. Look for `[RiskGuard] DAILY_LOSS_LIMIT_HIT` events.
4. **Sane PnL distribution** — open Trades tab → group by Win/Loss. Hopefully not 11% WR like Gemini's prior bug, but 30-50% WR range with R:R ~2.
5. **Telegram trail** — scroll through Telegram messages. Should be a clean entry/exit pair for each trade.

---

## 6. TEST PHASE 5 — ADAPTER SWITCH TEST (10 min)

Goal: verify you can hot-swap adapters without breaking anything.

### Step 5.1 — Stop live trader
Click **\"Stop\"** in Dashboard.

### Step 5.2 — Switch to Alpha Vantage
Configs tab → `data_source.yaml` → change `active_adapter: \"alphavantage\"` → Save.

### Step 5.3 — Start live trader again
Click **\"Start Live Trader\"**.

Boot log should show:
```
[INFO] Loading data adapter: alphavantage
[INFO] AlphaVantage API key validated OK
[INFO] 📊 NIFTY AI Bot Started (data: ALPHAVANTAGE, mode: PAPER)
```

### Step 5.4 — Verify forex prices

Dashboard's \"Live Price\" should now show EUR/USD around 1.08, not BTC at 105K. Sanity check passes.

### Step 5.5 — Switch back to Binance (or AngelOne if testing NSE start)

---

## 7. REVERT BEFORE TOMORROW MORNING (mandatory)

Before tomorrow 09:00 IST when you launch NSE paper trading:

```powershell
cd \"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\"
notepad config\data_source.yaml
# Set: active_adapter: \"angelone\"
# Save and close
```

Also revert any test env overrides:
```bash
# Remove from .env:
OVERRIDE_TIME_GATES_FOR_TEST=true
```

Confirm tomorrow morning checklist (per PHASE_25B_LAUNCH_PREP.md Section 4) passes with adapter=angelone.

---

## 8. WHAT TO REPORT BACK TO ME AFTER TONIGHT'S TEST

A single message with these answers:

```
1. Phase 1 (adapter CLI test): PASS / FAIL — error if any
2. Phase 2 (dashboard health): PASS / FAIL — screenshot if anything weird
3. Phase 3 (live trader dry-run):
   - First signal fired at: HH:MM IST
   - Trade executed: yes/no
   - Telegram alert received: yes/no
   - Trade exited via: TP / SL / EOD
   - Logged to paper_trades.jsonl: yes/no
4. Phase 4 (overnight, optional):
   - Total trades: ___
   - WR: ___%
   - Crashes: yes/no
5. Phase 5 (adapter switch):
   - Stop → Switch → Start cycle worked: yes/no
```

Based on your report I'll give the GREEN/AMBER/RED for tomorrow morning's NSE paper launch.

---

## 9. EMERGENCY ABORT

If at ANY point during tonight's test:
- Bot tries to place a real order (impossible by design, but check)
- Telegram messages spam (>20 in 1 min)
- Logs show repeated CRITICAL errors
- Dashboard shows negative capital

→ Click the **red KILL SWITCH** button in the Dashboard top-right.
→ Open Logs tab, screenshot the last 50 lines.
→ Upload screenshot here.

---

## 10. SUCCESS LOOKS LIKE THIS

By Saturday morning, you have:
- ✅ Bot has been running for 8+ hours on BTC/USDT data
- ✅ 5-15 paper trades logged in `paper_trades.jsonl`
- ✅ RiskGuard fired correctly when needed
- ✅ Telegram alerts arriving for every event
- ✅ Dashboard responsive throughout
- ✅ No crashes, no silent failures
- ✅ Adapter swap (Binance ↔ AlphaVantage) tested
- ✅ Reverted to AngelOne for tomorrow's NSE launch

If all 8 boxes ✅ → tomorrow 09:15 IST NSE paper trading launch is GREEN.

---

**END OF AFTER-HOURS TEST RUNBOOK.**
"
Observation: Create successful: /app/AFTERHOURS_TEST_RUNBOOK.md