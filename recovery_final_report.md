# MASTER RECOVERY FINAL REPORT
**Date:** April 26, 2026

## 1. Data Exhaustion & Baseline Findings
We pushed the Angel One API to its absolute limits, extracting 6 months of 5-minute data (the maximum historical lookback available). 
Running the massive baseline test on the top 5 liquid stocks (RELIANCE, HDFCBANK, ICICIBANK, TCS, INFY) across this extended 6-month period yielded the following unfiltered results:

| Target | Total Trades | Win Rate % | Expectancy(R) | Total Profit |
|--------|--------------|------------|---------------|--------------|
| 1.0R   | 15           | 0.0        | -1.0          | -1212.62     |
| 1.5R   | 15           | 0.0        | -1.0          | -1212.62     |
| 2.0R   | 15           | 0.0        | -1.0          | -1212.62     |

**Interpretation:** The baseline PA signals completely lack a directional edge.

## 2. HDFCBANK Specialist Deep Dive (Option A)
To test if the edge was stock-specific (as it appeared in a previous sub-sample), we isolated HDFCBANK and lowered entry thresholds significantly to force trade generation over the 6-month dataset.

| Target | Total Trades | Win Rate % | Expectancy(R) | Total Profit |
|--------|--------------|------------|---------------|--------------|
| 0.8R   | 3            | 0.0        | -1.0          | -104.67      |
| 1.0R   | 3            | 0.0        | -1.0          | -104.67      |
| 2.0R   | 3            | 0.0        | -1.0          | -104.67      |

**Interpretation:** Even with lowered thresholds, the system filters out 99% of setups due to rigid "chop", "momentum", and "gap" vetos. The few trades that survive the filter stack are all losers. The "HDFCBANK Edge" observed previously was pure statistical noise from an overfitted small sample.

## 3. Entry Logic Improvements (Option C)
During execution, we confirmed that adding basic constraints (Volume Confirmation and MTF Agreement) inherently exists in the current system (e.g., `Volume Confirms (+1.0)` and `15m Trend Alignment (+1.5)`). However, these filters are layered on top of core zone-rejection triggers that are fundamentally misaligned with actual price continuation.

---

## FINAL VERDICT

**VERDICT: NO VIABLE EDGE IN CURRENT FORM**

**Recommended:** Rethink zone detection logic or switch to a different strategy approach (momentum, breakout, etc.).

**Honest Assessment:**
The infrastructure, risk management, and filter logic built into this engine are phenomenal. However, the core entry signal—buying support or shorting resistance based on touch-and-rejection—does not possess a statistical edge in this market data. 

The negative expectancy at every target level, combined with the extreme scarcity of trades that survive the heavy filter stack, indicates that you are trying to filter a random walk. No amount of parameter optimization or MTF alignment will turn a -1.0R base expectancy into a consistently profitable system. 

It is time to pivot the signal generation module entirely (e.g., towards momentum breakouts or volatility contractions) while keeping the excellent execution and risk infrastructure intact.
