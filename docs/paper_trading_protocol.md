# Paper Trading Protocol — 60 Session Validation

## Objective
Validate the filtered strategy (TRAP_REVERSAL + selective ZONE_REJECTION) over 60 live sessions.

## Success Criteria (ALL must be met for Go-Live)
- [ ] Minimum 60 paper trades completed (average 1/day)
- [ ] Win rate >= 45%
- [ ] Expectancy >= +0.3R
- [ ] Profit Factor >= 1.5
- [ ] Max drawdown < 3% of capital
- [ ] 100% adherence to Strategy Filter (no manual overrides)

## Kill Criteria (Stop immediately if triggered)
- [ ] 5 consecutive losses
- [ ] Win rate drops below 30% after 20 trades
- [ ] Total drawdown exceeds 4% of capital
- [ ] System failure (data feed or logic crash) > 2 times

## Daily Checklist
1. 09:10 - Verify VIX and Index feeds are active.
2. 09:15 - Confirm Market Regime classification.
3. 15:30 - Run `scripts/audit_paper_trades.py` to check PnL.
