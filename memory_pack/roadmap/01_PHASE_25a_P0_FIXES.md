# 01 — Phase 25a: Audit P0 Cleanup
## 🎯 Objectives
Fix the 8 P0 bugs identified in the `AUDIT_REPORT_pre_paper_trade.md` to ensure the backtest baseline is valid before any live deployment.

## 📋 Requirements (User Items)
- **Item 25**: Fix logic error in trade entry timing.
- **Item 28**: Correct slippage model for high-volatility periods.
- **Item 41**: Resolve memory leak in long-running backtests.
- (Plus other 5 P0 bugs from Audit Report)

## 🧪 Tests
1. **Regression Backtest**: Run 6-month NIFTY backtest; results must match mathematical expectations.
2. **Memory Profile**: Run 24-hour simulation; heap usage must remain stable (< 200MB growth).
3. **P0 Validation**: Verify each specific fix against the audit's "Expected Behavior" column.

## 🏁 Acceptance Gate
- [ ] All 8 P0 bugs marked FIXED in Audit Report.
- [ ] Backtest Profit Factor (OOS) remains > 1.4.
- [ ] No new P0 or P1 bugs introduced.
- **Gate Result**: [PASS/FAIL]
