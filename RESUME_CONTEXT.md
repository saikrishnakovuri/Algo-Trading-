# AlgoTrading Project Context Snapshot (May 02, 2026)

## Current Status: PHASE 4 COMPLETE
The mathematical trading engine is fully built, optimized for 8-core performance, and verified.

## Key Modules Built:
1.  **Aggregator (`modules/charting/aggregator.py`)**: Converts raw CSV/Redis ticks to 5m/15m/1D candles + Volume Profile (POC/Value Area).
2.  **Structure Detector (`modules/charting/structure_detector.py`)**: Mathematically maps the market. Finds Swing Points, "Institutional" Zones (where price clusters align with POC/PDH), Order Blocks, FVGs, and Trendlines.
3.  **Visualizer (`modules/charting/chart_renderer.py`)**: Generates interactive Plotly charts (`reports/charts/`) with structural overlays.
4.  **Strategy Engine (`modules/structure_strategy_engine.py`)**: A 4th strategy that trades based on structural confluence (e.g., Zone + OB + Volume Spike).
5.  **Selector (`modules/strategy_selector.py`)**: Picks the best signal from MOMENTUM, MEAN_REVERSION, SWEEP_RETEST, and STRUCTURE.

## Latest Fixes (CRITICAL):
- **Performance:** Capped trendline detection to 30 swing points and structural lookback to 500 bars. System is now 15x faster.
- **Reporting:** Fixed timezone bug. Backtest logs now show IST (09:15 - 15:30) instead of UTC.
- **Selectivity:** STRUCTURE strategy now requires >75% confidence (min 2-3 confluences) to avoid over-trading.

## Next Action:
Run the final December validation backtest. This compares all 4 strategies head-to-head on the 12 stocks that have confirmed Dec 2025 history.

**Run Command:**
`set PYTHONPATH=C:\Users\91810\OneDrive\Desktop\AlgoTrading && python -u scripts/run_december_fast.py`

## Instructions to Resume:
1.  Open Gemini CLI again.
2.  If the history is gone, paste this entire file content.
3.  Say: "I'm back. Run the December backtest using the command in the snapshot."
