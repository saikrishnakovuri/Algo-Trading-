# Options Trading Bot: Project Context & Final Strategy (Phase 25 Recap)

## Project Status: **Pre-Deployment Validated**
**Date:** May 3, 2026
**Overall Goal:** Deploy a NIFTY/BANKNIFTY Options bot using the validated "Liquidity Trap" (Fakeout Fade) logic.

---

## 1. The Winning Strategy: "The Ultimate Step-Trail"
After 25 phases of optimization, the following logic has been proven profitable over 30+ unique trading days (Mar 10 – Apr 24, 2026).

### **Core Parameters**
- **Capital:** ₹1,00,000 (1 Lakh)
- **Engine:** `LIQUIDITY_TRAP` (Fades retail breakouts on Nifty/BankNifty).
- **Confidence Hurdle:** 70% Minimum.
- **Risk per Trade:** 2% of Current Capital (₹2,000 baseline).
- **Daily Constraints:** 
    - Max 5 trades per day.
    - **Stop trading for the day after 2 consecutive losses.**
    - Max 2 simultaneous positions.
- **Lot Size:** 65 (NIFTY) | 30 (BANKNIFTY) - *NSE 2026 Standards*.

### **Exit & Scaling Logic**
- **Initial SL:** 1.0x Hourly ATR proxy (2.5x of 5m ATR).
- **Target 1 (T1):** 1.5R (Risk-Reward).
- **Scaling:** **Sell 50% of quantity at T1.**
- **Trailing:** Move SL to **Breakeven** at T1. For the remaining 50%, follow a **0.5R Step-Trail**:
    - If price moves to 2.0R, SL moves to 1.5R.
    - If price moves to 2.5R, SL moves to 2.0R.
- **EOD Exit:** Hard exit at 15:15 IST.

---

## 2. Performance Summary (Final Validation)
| Metric | Result |
| :--- | :--- |
| **Period** | 30 Trading Sessions |
| **Total Trades** | 32 (Selective) |
| **Win Rate** | 12.5% (High RR makes up for this) |
| **Total Return** | **+42.26%** |
| **Max Daily Drawdown** | ~4% (Capped by 2-loss rule) |
| **Final Net P&L** | **+₹42,258** |

---

## 3. Architecture Overview (Ready for Integration)

### **Key Modules Created:**
1.  `modules/options/signal_adapter.py`: Adapts Price Action to Index Option signals.
2.  `modules/options/strike_selector.py`: Selects ATM/OTM and Next-Week expiries for theta protection.
3.  `modules/options/risk_manager.py`: Implements daily circuit breakers and confidence escalation.
4.  `modules/options/trade_executor.py`: High-frequency monitor for the Step-Trail and scaling logic.
5.  `live_options_trader.py`: The main loop (Brain) of the system.

### **Backtest Diagnostic Files:**
- `scripts/options_ultimate_validation.py`: The definitive logic checker.
- `scripts/compare_fade_vs_follow.py`: Proved Fading is superior for Nifty.

---

## 4. Plan for Tomorrow (Phase 26+)
1.  **Full Integration:** Finalize the wiring in `live_options_trader.py` to ensure the "2-loss stop" and "Step-Trail" work in live websocket streams.
2.  **Paper Trading Deploy:** Launch the bot in PAPER mode at 09:15 AM Monday.
3.  **Heartbeat Setup:** Connect Telegram notifications for the "Profit Lock" and "Circuit Breaker" alerts.

---

**File Path:** `C:\Users\91810\OneDrive\Desktop\AlgoTrading\OPTIONS_STRATEGY_CONTEXT.md`
