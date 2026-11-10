
Action: file_editor create /app/GEMINI_COMPREHENSIVE_BUGFIX_BACKTEST_PRODUCTION.md --file-text "# COMPREHENSIVE EXECUTION PROMPT — Bug Fix, Backtest, Production Readiness & Live Paper Trading

## YOUR IDENTITY

You are a **Senior Quantitative Trading Systems Engineer** with 15 years of experience in algorithmic trading, backtesting engines, and production deployment. You are meticulous, paranoid about bugs, and treat every line of code like it will handle real money — because it will.

**You will NOT stop until every phase below is COMPLETE. No shortcuts. No stubs. No \"TODO later.\"**

---

## PHASE 0: FULL CODEBASE AUDIT & BUG EXTERMINATION

### 0.1 — Discover ALL Files

```
ROOT: C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\
```

First, recursively scan and catalogue EVERY file in the project:

```python
import os

root = r\"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\"
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.endswith(('.py', '.md', '.csv', '.json', '.txt', '.yaml', '.yml', '.env', '.toml')):
            print(os.path.join(dirpath, f))
```

Create a file called `CODEBASE_AUDIT_REPORT.txt` and list every file found.

### 0.2 — Compile & Syntax Check EVERY Python File

For EVERY `.py` file found:

```bash
# Step 1: Syntax check
python -m py_compile <file.py>

# Step 2: Import check (catch missing dependencies)
python -c \"import importlib.util; spec = importlib.util.spec_from_file_location('mod', '<file.py>'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\"
```

**Log results in `CODEBASE_AUDIT_REPORT.txt`:**
```
[COMPILE] file.py — OK / FAIL: <error message>
[IMPORT]  file.py — OK / FAIL: <error message>
```

### 0.3 — Fix ALL Bugs Found

For each failure:
1. Read the error message
2. Open the file
3. Fix the bug (don't just comment it out)
4. Re-compile and re-import to confirm fix
5. Log the fix:
```
[FIX] file.py — Line 42: Fixed <description>. Was: <old>. Now: <new>.
```

### 0.4 — Dependency Check

```bash
pip install -r requirements.txt  # If exists
pip check                         # Check for dependency conflicts
```

If `requirements.txt` doesn't exist, create one by scanning all imports:
```bash
pip freeze > requirements.txt
```

### 0.5 — Common Bug Patterns to Hunt For

Scan every Python file for these known issues:

| Bug Pattern | What to Look For | Fix |
|---|---|---|
| **Import errors** | Missing modules, circular imports | Install or restructure |
| **Type mismatches** | String vs float in comparisons | Cast properly |
| **Off-by-one** | Wrong indexing in candle lookback | Verify index bounds |
| **NaN propagation** | Math on NaN without checking | Add `pd.notna()` guards |
| **Empty DataFrame** | `.iloc[-1]` on empty df | Add length check |
| **Division by zero** | ATR=0, range=0 | Add zero-division guards |
| **Hardcoded paths** | Windows paths that won't work cross-platform | Use `os.path.join()` or `pathlib` |
| **Missing return** | Functions that don't return on all paths | Add explicit return |
| **Mutable defaults** | `def f(x=[])` | Use `None` + internal init |
| **Datetime issues** | Naive vs aware datetimes | Standardize to UTC |
| **Signal format** | Inconsistent signal output formats | Ensure all use Signal dataclass |
| **Unused variables** | Dead code cluttering logic | Remove or comment why kept |

Run `pylint` or `ruff` on the entire codebase:
```bash
pip install ruff
ruff check . --fix
```

---

## PHASE 1: BACKTEST ENGINE AUDIT

### 1.1 — Locate the Backtest Engine

Find the backtest V1 engine. Likely locations:
```
- backtest_engine.py
- backtester.py  
- backtest_v1.py
- engine/backtest/
- Any file containing \"backtest\" in its name
```

```bash
# Find all backtest-related files
find . -type f -name \"*backtest*\" -o -name \"*backtester*\" | sort
grep -rl \"backtest\" --include=\"*.py\" . | sort
```

### 1.2 — Verify Backtest Engine Components

The backtest engine MUST have these components. If any are missing, BUILD THEM:

```
[CHECK] Data loader — Can load OHLCV data (CSV, API, or generated)
[CHECK] Strategy executor — Runs strategy.detect() on each candle/window
[CHECK] Order manager — Simulates market/limit orders
[CHECK] Position tracker — Tracks open positions, entry prices, quantities
[CHECK] P&L calculator — Calculates realized + unrealized P&L
[CHECK] Risk manager — Enforces stop loss, take profit, max positions
[CHECK] Trade logger — Records every trade with timestamp, entry, exit, P&L
[CHECK] Report generator — Produces summary statistics
[CHECK] CSV exporter — Saves detailed results to CSV
```

### 1.3 — Verify Data Source

Check what data source the backtest uses:
- Historical CSV files?
- API calls (yfinance, Zerodha Kite, etc.)?
- Generated/synthetic data?

**If no data exists**, use `yfinance` to download 3 months of data:

```python
import yfinance as yf

# Download NIFTY 50 / BANKNIFTY data — 3 months (Dec 2025, Jan 2026, Feb 2026)
# EXCLUDE March 2026 as instructed

# For index options backtesting, use these symbols:
symbols = {
    'NIFTY': '^NSEI',
    'BANKNIFTY': '^NSEBANK',
    # Add individual stocks if needed:
    'RELIANCE': 'RELIANCE.NS',
    'TCS': 'TCS.NS',
    'HDFCBANK': 'HDFCBANK.NS',
}

for name, ticker in symbols.items():
    df = yf.download(ticker, start='2025-12-01', end='2026-02-28', interval='15m')
    df.to_csv(f'data/{name}_15m_3months.csv')
    print(f\"Downloaded {name}: {len(df)} candles\")

# Also download daily data for higher timeframe analysis
for name, ticker in symbols.items():
    df = yf.download(ticker, start='2025-12-01', end='2026-02-28', interval='1d')
    df.to_csv(f'data/{name}_1d_3months.csv')
```

---

## PHASE 2: COMPREHENSIVE 3-MONTH BACKTEST

### 2.1 — Backtest Configuration

```python
BACKTEST_CONFIG = {
    # Time Period
    'start_date': '2025-12-01',
    'end_date': '2026-02-28',        # EXCLUDE March 2026
    'timeframes': ['15m', '1h'],      # Primary timeframes
    
    # Capital & Risk
    'initial_capital': 1000000,       # 10 Lakh INR (adjust as needed)
    'risk_per_trade': 0.02,           # 2% risk per trade
    'max_open_positions': 5,
    'max_daily_loss': 0.05,           # 5% max daily drawdown -> stop trading
    
    # Execution
    'slippage_bps': 5,                # 5 basis points slippage
    'commission_per_trade': 20,       # INR per order (Zerodha-like)
    'fill_delay_candles': 1,          # Execute on next candle (realistic)
    
    # Strategy Selection
    'run_all_strategies': True,       # Run all 48 strategies
    'min_confidence': 0.6,            # Only trade signals with 60%+ confidence
    
    # Output
    'output_csv': r'C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\backtest_detailed_results.csv',
    'output_summary': r'C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\backtest_summary_report.txt',
}
```

### 2.2 — Run the Backtest

Execute the backtest with ALL strategies active:

```python
from engine.strategy_engine import PriceActionEngine
from backtest_engine import BacktestEngine  # or whatever the backtest module is called

engine = PriceActionEngine()
backtester = BacktestEngine(config=BACKTEST_CONFIG)

# Run on each symbol
results = {}
for symbol in ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK']:
    print(f\"\n{'='*60}\")
    print(f\"BACKTESTING: {symbol}\")
    print(f\"{'='*60}\")
    
    result = backtester.run(
        symbol=symbol,
        engine=engine,
        timeframe='15m'
    )
    results[symbol] = result
    
    # Print quick summary
    print(f\"  Total Trades: {result['total_trades']}\")
    print(f\"  Win Rate: {result['win_rate']:.1%}\")
    print(f\"  Net P&L: ₹{result['net_pnl']:,.2f}\")
    print(f\"  Max Drawdown: {result['max_drawdown']:.1%}\")
    print(f\"  Sharpe Ratio: {result['sharpe_ratio']:.2f}\")
```

### 2.3 — Output CSV Format

The detailed results CSV (`backtest_detailed_results.csv`) MUST contain these columns:

```
trade_id, symbol, strategy_name, strategy_category, signal_type, confidence,
entry_datetime, entry_price, exit_datetime, exit_price,
stop_loss, take_profit, position_size, quantity,
gross_pnl, commission, slippage_cost, net_pnl,
holding_period_minutes, risk_reward_achieved,
win_loss (W/L), capital_after_trade, drawdown_at_trade,
timeframe, market_regime, notes
```

Save to: `C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\backtest_detailed_results.csv`

### 2.4 — Summary Report

Generate `backtest_summary_report.txt`:

```
================================================================
  PRICE ACTION STRATEGY ENGINE — BACKTEST REPORT
  Period: Dec 1, 2025 — Feb 28, 2026 (3 Months)
  Generated: [TIMESTAMP]
================================================================

OVERALL PERFORMANCE
-------------------
  Initial Capital:     ₹10,00,000
  Final Capital:       ₹XX,XX,XXX
  Net P&L:             ₹X,XX,XXX (+XX.X%)
  Total Trades:        XXX
  Winning Trades:      XXX (XX.X%)
  Losing Trades:       XXX (XX.X%)
  Avg Win:             ₹X,XXX
  Avg Loss:            ₹X,XXX
  Largest Win:         ₹XX,XXX
  Largest Loss:        ₹XX,XXX
  Profit Factor:       X.XX
  Sharpe Ratio:        X.XX
  Sortino Ratio:       X.XX
  Max Drawdown:        XX.X% (₹X,XX,XXX)
  Max Drawdown Duration: XX days
  Recovery Factor:     X.XX
  Avg Holding Period:  XX minutes
  Risk-Reward (Avg):   X:X

PER-SYMBOL BREAKDOWN
---------------------
  Symbol     | Trades | Win% | Net P&L    | Sharpe | MaxDD
  -----------|--------|------|------------|--------|------
  NIFTY      |   XX   | XX%  | ₹X,XX,XXX | X.XX   | XX%
  BANKNIFTY  |   XX   | XX%  | ₹X,XX,XXX | X.XX   | XX%
  RELIANCE   |   XX   | XX%  | ₹X,XX,XXX | X.XX   | XX%
  TCS        |   XX   | XX%  | ₹X,XX,XXX | X.XX   | XX%
  HDFCBANK   |   XX   | XX%  | ₹X,XX,XXX | X.XX   | XX%

PER-STRATEGY BREAKDOWN (Top 10 by P&L)
---------------------------------------
  Strategy               | Category    | Trades | Win% | Net P&L    | Confidence
  -----------------------|-------------|--------|------|------------|----------
  1. ...                 | ...         |   XX   | XX%  | ₹X,XX,XXX | 0.XX
  2. ...                 | ...         |   XX   | XX%  | ₹X,XX,XXX | 0.XX
  ...

PER-STRATEGY BREAKDOWN (Bottom 5 — worst performers)
-----------------------------------------------------
  Strategy               | Category    | Trades | Win% | Net P&L     | Action
  -----------------------|-------------|--------|------|-------------|--------
  1. ...                 | ...         |   XX   | XX%  | -₹X,XX,XXX | DISABLE
  ...

PER-CATEGORY BREAKDOWN
-----------------------
  Category                   | Trades | Win% | Net P&L    | Best Strategy
  ---------------------------|--------|------|------------|---------------
  Advanced Concepts          |   XX   | XX%  | ₹X,XX,XXX | ...
  Candlestick Patterns       |   XX   | XX%  | ₹X,XX,XXX | ...
  Price Action Patterns      |   XX   | XX%  | ₹X,XX,XXX | ...
  Support & Resistance       |   XX   | XX%  | ₹X,XX,XXX | ...

MONTHLY BREAKDOWN
-----------------
  Month     | Trades | Win% | Net P&L    | MaxDD
  ----------|--------|------|------------|------
  Dec 2025  |   XX   | XX%  | ₹X,XX,XXX | XX%
  Jan 2026  |   XX   | XX%  | ₹X,XX,XXX | XX%
  Feb 2026  |   XX   | XX%  | ₹X,XX,XXX | XX%

RISK METRICS
-------------
  Value at Risk (95%):   ₹X,XXX per day
  Expected Shortfall:    ₹X,XXX per day
  Win Streak (Max):      XX trades
  Loss Streak (Max):     XX trades
  Consecutive Loss Days: XX days

RECOMMENDATIONS
---------------
  [Based on backtest results, list strategies to keep/disable/tune]
```

---

## PHASE 3: COMPREHENSIVE TESTING — ALL POSSIBLE TESTS

**Run EVERY test type below. Do NOT skip any.**

### 3.1 — Unit Tests (Per Strategy)

```bash
pytest engine/tests/ -v --tb=short -q
```

Every strategy MUST have:
- Smoke test (instantiation, returns list)
- Bullish detection test
- Bearish detection test
- Edge case tests (empty df, flat market, NaN values)
- Signal format validation test
- Confidence range test (0.0-1.0)
- Stop loss / take profit calculation test

### 3.2 — Integration Tests

```python
\"\"\"Test that the full engine pipeline works end-to-end.\"\"\"

def test_engine_initialization():
    \"\"\"All 48 strategies register without errors.\"\"\"
    engine = PriceActionEngine()
    strategies = engine.list_strategies()
    total = sum(len(v) for v in strategies.values())
    assert total == 48, f\"Expected 48 strategies, got {total}\"

def test_engine_analyze_returns_signal():
    \"\"\"engine.analyze() returns a valid Signal object.\"\"\"
    engine = PriceActionEngine()
    df = load_sample_data()  # 200 candles of NIFTY 15m
    signal = engine.analyze(df, timeframe='15m')
    assert isinstance(signal, Signal)
    assert signal.signal_type in SignalType
    assert 0.0 <= signal.confidence <= 1.0

def test_engine_full_report():
    \"\"\"engine.full_report() returns complete dict with all keys.\"\"\"
    engine = PriceActionEngine()
    df = load_sample_data()
    report = engine.full_report(df, timeframe='15m')
    required_keys = ['timestamp', 'timeframe', 'market_regime', 'final_signal',
                     'strategies_run', 'total_signals', 'confluence_score']
    for key in required_keys:
        assert key in report, f\"Missing key: {key}\"

def test_all_strategies_detect_without_crash():
    \"\"\"Run every strategy on real data — none should crash.\"\"\"
    engine = PriceActionEngine()
    df = load_sample_data()
    for name, strategy in engine.registry.get_all().items():
        try:
            signals = strategy.detect(df, '15m')
            assert isinstance(signals, list)
        except Exception as e:
            pytest.fail(f\"Strategy '{name}' crashed: {e}\")
```

### 3.3 — Backtest Validation Tests

```python
\"\"\"Validate that backtest results are realistic and not garbage.\"\"\"

def test_no_future_leaking():
    \"\"\"
    Ensure no strategy uses future data.
    Method: Run strategy on data[0:100], then data[0:101].
    Signals at candle 100 should be identical.
    \"\"\"
    pass

def test_pnl_math_is_correct():
    \"\"\"
    For each trade in backtest_detailed_results.csv:
    - gross_pnl = (exit_price - entry_price) * quantity * direction
    - net_pnl = gross_pnl - commission - slippage_cost
    - Verify capital_after_trade = previous_capital + net_pnl
    \"\"\"
    import pandas as pd
    results = pd.read_csv('backtest_detailed_results.csv')
    for i, row in results.iterrows():
        direction = 1 if row['signal_type'] in ['BUY', 'STRONG_BUY'] else -1
        expected_gross = (row['exit_price'] - row['entry_price']) * row['quantity'] * direction
        assert abs(row['gross_pnl'] - expected_gross) < 0.01, f\"Trade {row['trade_id']}: P&L math wrong\"

def test_no_overlapping_trades():
    \"\"\"Same symbol should not have conflicting positions.\"\"\"
    pass

def test_stop_loss_honored():
    \"\"\"Every losing trade should have exited at or near stop_loss.\"\"\"
    pass

def test_max_positions_respected():
    \"\"\"Never more than max_open_positions at any time.\"\"\"
    pass

def test_max_daily_loss_respected():
    \"\"\"Trading should stop when daily loss exceeds limit.\"\"\"
    pass

def test_realistic_fill_prices():
    \"\"\"Entry/exit prices should be within candle range, not at exact high/low.\"\"\"
    pass

def test_no_weekend_trades():
    \"\"\"No trades executed on Saturday/Sunday.\"\"\"
    pass

def test_no_after_hours_trades():
    \"\"\"No trades outside market hours (9:15 AM - 3:30 PM IST for NSE).\"\"\"
    pass
```

### 3.4 — Stress Tests

```python
\"\"\"Push the engine to its limits.\"\"\"

def test_high_volatility_data():
    \"\"\"Feed data with 5% candles — engine should not crash or give absurd signals.\"\"\"
    pass

def test_gap_up_gap_down():
    \"\"\"Feed data with large gaps between candles.\"\"\"
    pass

def test_very_low_volume():
    \"\"\"Feed data with near-zero volume.\"\"\"
    pass

def test_1000_candles_performance():
    \"\"\"engine.analyze() with 1000 candles should complete in < 5 seconds.\"\"\"
    import time
    start = time.time()
    engine.analyze(large_df, '15m')
    elapsed = time.time() - start
    assert elapsed < 5.0, f\"Too slow: {elapsed:.1f}s\"

def test_rapid_fire_calls():
    \"\"\"Call engine.analyze() 100 times rapidly — no memory leaks, consistent results.\"\"\"
    pass
```

### 3.5 — Data Integrity Tests

```python
\"\"\"Verify data quality before trusting backtest results.\"\"\"

def test_no_nan_in_ohlcv():
    \"\"\"OHLCV data has no NaN values.\"\"\"
    pass

def test_ohlc_consistency():
    \"\"\"For every candle: low <= open <= high, low <= close <= high.\"\"\"
    pass

def test_chronological_order():
    \"\"\"Data is sorted by timestamp ascending.\"\"\"
    pass

def test_no_duplicate_timestamps():
    \"\"\"No duplicate candles.\"\"\"
    pass

def test_no_gaps_in_data():
    \"\"\"No unexpected gaps in the time series (weekends/holidays excluded).\"\"\"
    pass
```

### 3.6 — Run ALL Tests

```bash
# Run everything with verbose output
pytest -v --tb=long --strict-markers -x 2>&1 | tee test_results_full.txt

# Generate HTML report if pytest-html is installed
pip install pytest-html
pytest --html=test_report.html --self-contained-html

# Log results
echo \"TOTAL TESTS: $(grep -c 'PASSED\|FAILED' test_results_full.txt)\" >> CODEBASE_AUDIT_REPORT.txt
echo \"PASSED: $(grep -c 'PASSED' test_results_full.txt)\" >> CODEBASE_AUDIT_REPORT.txt
echo \"FAILED: $(grep -c 'FAILED' test_results_full.txt)\" >> CODEBASE_AUDIT_REPORT.txt
```

**ALL TESTS MUST PASS BEFORE MOVING TO PHASE 4.**

If tests fail:
1. Fix the bug
2. Re-run ONLY the failed test to confirm fix
3. Re-run ALL tests to confirm no regressions
4. Repeat until 100% pass rate

---

## PHASE 4: PRODUCTION READINESS CHECKLIST

### 4.1 — Code Quality

```
[ ] All Python files compile without errors
[ ] No syntax errors anywhere
[ ] No unused imports
[ ] No circular imports
[ ] All functions have docstrings
[ ] Type hints on all public methods
[ ] No hardcoded file paths (use config or environment variables)
[ ] No print() statements in production code (use logging)
[ ] Proper error handling (try/except with specific exceptions)
[ ] No bare except clauses
```

### 4.2 — Strategy Engine

```
[ ] All 48 strategies load and register
[ ] Each strategy has name, category, detect() implemented
[ ] Signal dataclass is consistent across all strategies
[ ] Strategy selector correctly identifies market regime
[ ] Signal aggregator handles confluence properly
[ ] Engine.analyze() returns valid signals
[ ] Engine.full_report() returns complete analysis
[ ] No strategy uses future data (look-ahead bias)
[ ] Confidence scores are meaningful (not all 1.0 or all 0.5)
[ ] Stop loss and take profit are calculated where applicable
```

### 4.3 — Backtest Engine

```
[ ] Backtest runs without errors for 3 months of data
[ ] P&L calculations are mathematically correct
[ ] Slippage and commission are accounted for
[ ] Position sizing follows risk rules
[ ] Max position limits enforced
[ ] Daily loss limits enforced
[ ] Trade log CSV is complete and correct
[ ] Summary report is generated
[ ] Results saved to correct path (backtest_detailed_results.csv)
[ ] Results match the format from previous backtest
```

### 4.4 — Data Pipeline

```
[ ] Data download works (yfinance or existing source)
[ ] Data is cleaned (no NaN, no duplicates)
[ ] OHLCV format is consistent
[ ] Multiple timeframes supported
[ ] Multiple symbols supported
[ ] Data cached to avoid redundant downloads
```

### 4.5 — Logging & Monitoring

```
[ ] Logging configured (file + console)
[ ] Trade entries logged
[ ] Trade exits logged
[ ] Errors logged with full traceback
[ ] Performance metrics logged
[ ] No sensitive data in logs
```

---

## PHASE 5: LIVE PAPER TRADING READINESS

### 5.1 — Broker Connection Check

Verify the connection to the live trading system (Zerodha Kite / Alpaca / whatever is configured):

```python
\"\"\"
Broker connection checklist:
\"\"\"

# 1. API credentials present
assert os.environ.get('BROKER_API_KEY') or config.get('api_key'), \"Missing API key\"
assert os.environ.get('BROKER_API_SECRET') or config.get('api_secret'), \"Missing API secret\"

# 2. Can authenticate
broker = BrokerConnection(config)
assert broker.authenticate(), \"Authentication failed\"

# 3. Can fetch live data
live_data = broker.get_ohlcv('NIFTY', '15m', limit=10)
assert len(live_data) > 0, \"Cannot fetch live data\"

# 4. Can place paper order (if paper trading mode exists)
if broker.is_paper_mode():
    order = broker.place_order(symbol='NIFTY', side='BUY', qty=1, order_type='MARKET')
    assert order.get('order_id'), \"Paper order failed\"
    broker.cancel_order(order['order_id'])

# 5. Can fetch positions
positions = broker.get_positions()
assert isinstance(positions, list), \"Cannot fetch positions\"

# 6. Can fetch account info
account = broker.get_account()
assert 'balance' in account or 'capital' in account, \"Cannot fetch account\"
```

### 5.2 — Live Pipeline Architecture

Verify this pipeline exists and works:

```
[Data Feed] → [OHLCV Builder] → [Strategy Engine] → [Signal] → [Risk Check] → [Order Execution] → [Position Monitor] → [Exit Logic]
      ↓                                                                                ↓
  [Tick/Candle Stream]                                                          [Trade Logger]
      ↓                                                                                ↓
  [WebSocket / API Poll]                                                        [P&L Tracker]
```

Each component must be:
- **Connected** (imports work, configs loaded)
- **Tested** (unit test exists and passes)
- **Logged** (every action produces a log entry)
- **Error-handled** (failures don't crash the bot)

### 5.3 — Paper Trading Configuration

Create/verify `paper_trading_config.yaml` (or `.json`):

```yaml
mode: PAPER                        # PAPER or LIVE — MUST be PAPER for testing
broker: zerodha                    # or alpaca, or whatever
symbols:
  - NIFTY
  - BANKNIFTY
timeframes:
  - 15m
  - 1h

capital: 1000000                   # Paper capital
risk_per_trade: 0.02               # 2%
max_open_positions: 5
max_daily_loss: 0.05               # 5% -> stop for day

engine:
  min_confidence: 0.65             # Only trade 65%+ confidence signals
  use_selector: true               # Use intelligent strategy selection
  confluence_required: 2           # At least 2 strategies must agree

execution:
  order_type: MARKET               # MARKET or LIMIT
  slippage_buffer_bps: 10          # Extra buffer for live execution
  
logging:
  level: INFO
  file: logs/paper_trading.log
  trade_log: logs/paper_trades.csv
  
alerts:
  enabled: true
  on_trade: true
  on_daily_summary: true
  on_error: true
```

### 5.4 — Final System Test

```python
\"\"\"
Run a simulated live session using the most recent 1 day of historical data
as if it were live. This is the FINAL gate before paper trading.
\"\"\"

def simulate_live_session():
    \"\"\"
    1. Load last 1 day of 15m candles
    2. Feed them one-by-one to the engine (simulating real-time)
    3. Execute paper trades on signals
    4. Log everything
    5. At the end, verify:
       - No crashes
       - Trades were logged
       - P&L is tracked
       - Risk limits were respected
    \"\"\"
    engine = PriceActionEngine()
    paper_broker = PaperBroker(capital=1000000)
    
    candles = load_last_day_data('NIFTY', '15m')
    
    for i in range(50, len(candles)):
        window = candles.iloc[:i+1]
        signal = engine.analyze(window, timeframe='15m')
        
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            paper_broker.buy(signal)
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            paper_broker.sell(signal)
        
        # Check open positions for exit
        paper_broker.check_exits(window.iloc[-1])
    
    # Verify session
    assert paper_broker.trade_count > 0, \"No trades executed — something is wrong\"
    assert paper_broker.get_capital() > 0, \"Capital went to zero — catastrophic\"
    print(f\"Simulation complete: {paper_broker.trade_count} trades, P&L: ₹{paper_broker.get_pnl():,.2f}\")
    
    return paper_broker.get_trade_log()
```

---

## PHASE 6: DEPLOYMENT PREP (LOCAL RUN + VERCEL)

### 6.1 — Local Run Instructions

Create a file called `HOW_TO_RUN.md`:

```markdown
# How to Run the Price Action Strategy Engine

## Prerequisites
- Python 3.10+
- pip (Python package manager)

## Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables (create .env file)
BROKER_API_KEY=your_key_here
BROKER_API_SECRET=your_secret_here
PAPER_MODE=true

# 3. Run backtest (to verify everything works)
python run_backtest.py

# 4. Run paper trading bot
python run_paper_trading.py

# 5. Run with dashboard (if web UI exists)
python app.py
# Then open http://localhost:8000
```

## Quick Test
```bash
# Run all tests
pytest -v

# Run specific test
pytest engine/tests/test_candlestick_patterns/ -v

# Run backtest only
python run_backtest.py --symbol NIFTY --period 3m
```

## Files You Should Check
- `backtest_detailed_results.csv` — Detailed trade log
- `backtest_summary_report.txt` — Performance summary  
- `logs/paper_trading.log` — Live paper trading log
- `CODEBASE_AUDIT_REPORT.txt` — Code audit results
- `building_strategies_using_master_md_file.txt` — Strategy build progress
```

### 6.2 — Vercel Deployment Prep (if web dashboard exists)

```
[ ] Frontend builds without errors: npm run build / yarn build
[ ] API routes work in serverless mode
[ ] Environment variables configured in Vercel dashboard
[ ] No file system writes in serverless functions (use DB instead)
[ ] CORS configured for Vercel domain
[ ] Build output is < 50MB (Vercel limit)
[ ] vercel.json configured correctly
```

Create `vercel.json` if needed:
```json
{
  \"builds\": [
    { \"src\": \"api/**/*.py\", \"use\": \"@vercel/python\" },
    { \"src\": \"frontend/package.json\", \"use\": \"@vercel/static-build\" }
  ],
  \"routes\": [
    { \"src\": \"/api/(.*)\", \"dest\": \"/api/$1\" },
    { \"src\": \"/(.*)\", \"dest\": \"/frontend/$1\" }
  ]
}
```

---

## PHASE 7: FINAL CHECKPOINT — THE GATE

Before declaring DONE, verify ALL of these:

```
CODEBASE AUDIT
  [x] Every .py file compiles
  [x] Every .py file imports without errors
  [x] All bugs found are fixed
  [x] ruff/pylint clean

STRATEGY ENGINE
  [x] 48/48 strategies implemented
  [x] 48/48 strategies tested
  [x] Engine.analyze() works
  [x] Engine.full_report() works
  [x] Strategy selector works

BACKTEST (3 MONTHS)
  [x] Ran Dec 2025 — Feb 2026 (March excluded)
  [x] Results saved to backtest_detailed_results.csv
  [x] Summary report generated
  [x] P&L math verified
  [x] No look-ahead bias
  [x] Risk limits honored

TESTS
  [x] All unit tests pass
  [x] All integration tests pass
  [x] All backtest validation tests pass
  [x] All stress tests pass
  [x] All data integrity tests pass
  [x] 100% pass rate — ZERO failures

PRODUCTION READINESS
  [x] No hardcoded paths
  [x] Logging configured
  [x] Error handling in place
  [x] Config externalized
  [x] requirements.txt up to date

PAPER TRADING READINESS
  [x] Broker connection verified (or ready to connect)
  [x] Paper trading config created
  [x] Simulated live session passed
  [x] HOW_TO_RUN.md created

OUTPUT FILES
  [x] CODEBASE_AUDIT_REPORT.txt
  [x] backtest_detailed_results.csv
  [x] backtest_summary_report.txt
  [x] building_strategies_using_master_md_file.txt (all checked)
  [x] test_results_full.txt
  [x] HOW_TO_RUN.md
  [x] paper_trading_config.yaml
```

---

## EXECUTION ORDER SUMMARY

```
PHASE 0: Scan → Compile → Fix ALL bugs → Dependency check
    ↓
PHASE 1: Find backtest engine → Verify components → Get data
    ↓
PHASE 2: Configure → Run 3-month backtest → Save CSV → Generate report
    ↓
PHASE 3: Unit tests → Integration tests → Backtest validation → Stress tests → Data tests → ALL MUST PASS
    ↓
PHASE 4: Code quality → Engine checks → Backtest checks → Data pipeline → Logging
    ↓
PHASE 5: Broker connection → Pipeline verification → Paper config → Simulated session
    ↓
PHASE 6: HOW_TO_RUN.md → Vercel prep (if applicable)
    ↓
PHASE 7: Final gate checklist — EVERYTHING must be [x]
```

---

## YOU HAVE YOUR ORDERS. START WITH PHASE 0. DO NOT STOP UNTIL PHASE 7 GATE IS 100% CHECKED.

**This is production code. This will trade real money after paper testing. Treat it accordingly.**

**START NOW.**
"
Observation: Create successful: /app/GEMINI_COMPREHENSIVE_BUGFIX_BACKTEST_PRODUCTION.md