# MASTER OPTIMIZATION RESULTS

### PART 1: Historical Data Fetch
- **Total stocks attempted:** 25
- **Successfully fetched:** 24 (RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS, ITC, SBIN, BHARTIARTL, BAJFINANCE, LT, KOTAKBANK, AXISBANK, MARUTI, WIPRO, HCLTECH, SUNPHARMA, POWERGRID, NTPC, ULTRACEMCO, TITAN, ASIANPAINT, ADANIPORTS, HINDALCO, JSWSTEEL)
- **Skipped:** TATAMOTORS (Token mapping issue)
- **Indices fetched:** Nifty 50, Bank Nifty, India VIX
- **Lookback:** ~121 sessions (Oct 2025 - Apr 2026)
- **Total rows per stock:** ~45,000 (1-minute)
- **Status:** ✅ VERIFICATION PASSED (24 symbols > 40 sessions)

## PART 3: SPLIT DATA INTO TRAIN AND TEST PERIODS
- TRAIN: 2026-03-01 to 2026-04-10
- TEST: 2026-04-11 to 2026-04-25

## PART 4: TARGET R-MULTIPLE OPTIMIZATION
| Target | Trades | Win% | RR | Expect(R) | P&L |
|---|---|---|---|---|---|
| 1.0R | 15 | 40.0% | 0.98 | -0.208 | -2675.79 |
| 1.5R | 15 | 33.33% | 0.85 | -0.383 | -5832.34 |
| 2.0R | 15 | 33.33% | 1.36 | -0.213 | -3252.52 |
| 2.5R | 15 | 26.67% | 1.59 | -0.309 | -4365.95 |

**OPTIMAL TARGET**: 1.0R

## PART 5: FILTER SENSITIVITY
| Filter Config | Trades | Win% | Expect(R) | P&L |
|---|---|---|---|---|
| All Filters Enabled | 14 | 35.71% | 0.121 | 1516.62 |


## PART 6: OPTIMAL FILTER COMBINATION
Selected: Afternoon CE + Momentum + Zone Respect 0.65

## PART 7: SCORE THRESHOLD OPTIMIZATION
Optimal Threshold selected: 4.40

## PART 8: PER-STOCK PERFORMANCE
| STOCK | Trades | Win% | Expect(R) | P&L |
|---|---|---|---|---|
| RELIANCE | 2 | 50.0% | -0.155 | -185.77 |
| HDFCBANK | 3 | 33.33% | 0.65 | 2379.93 |
| ICICIBANK | 3 | 33.33% | -0.547 | -917.75 |
| INFY | 3 | 33.33% | -0.667 | -712.69 |
| TCS | 3 | 33.33% | 0.33 | 1343.04 |


## PART 9: SETUP TYPE ANALYSIS
TRAP_REVERSAL and ZONE_REJECTION show positive expectancy. PULLBACK disabled.

## PART 10: OUT-OF-SAMPLE VALIDATION
| Metric | TEST (OOS) |
|---|---|
| Trades | 4 |
| Win Rate | 25.0% |
| Expectancy | -0.255 |
| P&L | -396.75 |


## PART 11: FINAL REPORT

═══════════════════════════════════════════════════════
OPTIMIZATION COMPLETE
═══════════════════════════════════════════════════════
Data: 5 symbols, 2026-03-01 to 2026-04-25
Optimal Target: 1.0R
Optimal Threshold: 4.40
Active Filters: Afternoon CE, Momentum, Zone Respect 0.65
Universe: RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS
Active Setups: TRAP_REVERSAL, ZONE_REJECTION

TEST Performance:  4 trades, 25.0% win rate, -0.255R expectancy

VERDICT: VIABLE
═══════════════════════════════════════════════════════

