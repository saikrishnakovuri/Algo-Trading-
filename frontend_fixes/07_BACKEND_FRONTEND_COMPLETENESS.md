Now I have the complete picture. Let me create the comprehensive MD file:
Action: file_editor create /app/frontend_fixes/07_BACKEND_FRONTEND_COMPLETENESS.md --file-text "# BACKEND → FRONTEND COMPLETENESS AUDIT & FIX
## For EVERY backend component that runs, there MUST be a frontend component to interact with it and view it

---

## MISSION

1. Read EVERY backend file: `server.py`, `backtest_engine.py`, `live_state.py`, `risk_calculator.py`, `notification_service.py`
2. Read EVERY module: All 35 `.py` files in `modules/` + 12 sub-packages
3. Read `dashboard/app.py`, `dashboard/charts.py`, `dashboard/loader.py`
4. Extract EVERY API route, EVERY function that produces viewable data, EVERY state that can be monitored
5. For each one → check if a frontend component exists that calls it
6. If NO frontend component exists → CREATE ONE
7. If frontend component exists but button is broken/disabled → FIX IT

**STRICTLY DO NOT CHANGE ANY BACKEND LOGIC. Only ADD frontend components and ADD new API routes to expose hidden backend data.**

---

## STEP 1: EXTRACT ALL BACKEND CAPABILITIES

### 1A — Read `AlgoTradingTelegramBotAndFrontend/backend/server.py`

```bash
# Extract every API route
grep -n \"@app\.\(get\|post\|put\|delete\|patch\|websocket\)\" AlgoTradingTelegramBotAndFrontend/backend/server.py
```

For EACH route found, create an entry:

```
ROUTE: GET /api/something
PURPOSE: Returns XYZ data
FRONTEND EXISTS: YES/NO
COMPONENT: ComponentName.js (if exists)
BUTTON/VIEW: \"Button label\" or \"Data table\" or \"Chart\"
STATUS: WORKING / BROKEN / MISSING
```

### 1B — Read `AlgoTradingTelegramBotAndFrontend/backend/backtest_engine.py`

```bash
# Find all public methods
grep -n \"def \" AlgoTradingTelegramBotAndFrontend/backend/backtest_engine.py | grep -v \"def _\"
```

Each public method = a capability that should be triggerable from frontend:
- `run_backtest()` → \"Run Backtest\" button
- `get_results()` → \"View Results\" table
- `export_results()` → \"Export\" button
- etc.

### 1C — Read `AlgoTradingTelegramBotAndFrontend/backend/live_state.py`

```bash
grep -n \"def \" AlgoTradingTelegramBotAndFrontend/backend/live_state.py | grep -v \"def _\"
```

Each method = live trading state that should be VISIBLE in frontend:
- `get_open_positions()` → Positions panel
- `get_pnl()` → P&L display
- `get_bot_status()` → Status indicator
- `get_active_trades()` → Active trades list
- etc.

### 1D — Read `AlgoTradingTelegramBotAndFrontend/backend/risk_calculator.py`

```bash
grep -n \"def \" AlgoTradingTelegramBotAndFrontend/backend/risk_calculator.py | grep -v \"def _\"
```

- `calculate_position_size()` → Risk calculator widget
- `get_risk_metrics()` → Risk dashboard panel
- etc.

### 1E — Read `AlgoTradingTelegramBotAndFrontend/backend/notification_service.py`

```bash
grep -n \"def \" AlgoTradingTelegramBotAndFrontend/backend/notification_service.py | grep -v \"def _\"
```

- `get_alerts()` → Alerts panel
- `send_alert()` → Manual alert button
- `get_alert_history()` → Alert history table
- etc.

### 1F — Read `dashboard/app.py`

```bash
grep -n \"@app\.\|def \" dashboard/app.py | grep -v \"def _\"
```

### 1G — Scan ALL 35 modules/ files

```bash
for f in modules/*.py; do
    echo \"=== $f ===\"
    grep -n \"def \" \"$f\" | grep -v \"def _\" | head -10
done
```

Key modules that MUST have frontend visibility:

| Module | What It Does | Frontend Needs |
|---|---|---|
| `price_action_engine.py` | Detects PA patterns | View detected patterns, pattern history |
| `decision_engine.py` | Makes trade decisions | View decision log, why trade was taken/rejected |
| `strategy_selector.py` | Selects active strategies | Strategy toggle panel |
| `strategy_router.py` | Routes signals | Signal routing log |
| `strategy_definitions.py` | Strategy configs | Strategy config editor |
| `candlestick_engine.py` | Detects candle patterns | Candle pattern viewer |
| `momentum_engine.py` | Momentum analysis | Momentum indicator panel |
| `mean_reversion_engine.py` | Mean reversion signals | MR signal viewer |
| `structure_strategy_engine.py` | Market structure | Structure analysis viewer |
| `sweep_retest_engine.py` | Sweep & retest patterns | Pattern detection viewer |
| `broker_layer.py` | Broker connection | Connection status, order history |
| `risk_guard.py` | Risk checks | Risk guard status, blocked trades log |
| `trailing_sl_manager.py` | Trailing SL tracking | Active trailing stops panel |
| `regime_gate.py` | Market regime | Current regime display |
| `indicator_engine.py` | Technical indicators | Indicator values display |
| `portfolio_manager.py` | Portfolio tracking | Portfolio overview, allocations |
| `confidence_scorer.py` | Signal confidence | Confidence breakdown |
| `context_detector.py` | Market context | Current context display |
| `option_chain.py` | Options chain data | Options chain viewer |
| `vix_filter.py` | VIX-based filtering | VIX status, filter state |
| `websocket_manager.py` | Live data feed | Connection status indicator |
| `dashboard_bridge.py` | Bridge to dashboard | N/A (infrastructure) |
| `data_layer.py` | Data access | Data status, cache info |
| `alert.py` | Alerts system | Alerts panel |
| `ai_analysis.py` | AI-powered analysis | AI analysis viewer |
| `learning.py` / `strategy_learner.py` | Strategy learning | Learning progress, parameter evolution |
| `event_calendar.py` | Market events | Event calendar widget |

**Sub-packages that need frontend:**

| Package | Components | Frontend Needs |
|---|---|---|
| `modules/smc/` | Order blocks, FVG, liquidity, structure | SMC analysis panel |
| `modules/regime/` | Classifier, HMM, rule layer | Regime status widget |
| `modules/risk_exec/` | Breaker, executor, sizer, trailing | Risk execution dashboard |
| `modules/context_filters/` | Calendar, chop, gap, time | Filter status indicators |
| `modules/intermarket/` | Breadth, sector, relative strength | Intermarket analysis panel |
| `modules/vp_avwap/` | Volume profile, AVWAP | VP/AVWAP analysis viewer |
| `modules/options/` | Strike selector, trade executor | Options execution panel |
| `modules/charting/` | Chart renderer, aggregator | Chart generation trigger |
| `modules/reporting/` | Daily report, equity tracker | Reports viewer |

---

## STEP 2: SCAN FRONTEND FOR EXISTING COMPONENTS

```bash
# Find all React component files
find AlgoTradingTelegramBotAndFrontend/frontend/src -name \"*.js\" -o -name \"*.jsx\" -o -name \"*.tsx\" | grep -v node_modules | sort

# For each component, extract what API it calls
for f in $(find AlgoTradingTelegramBotAndFrontend/frontend/src -name \"*.js\" -o -name \"*.jsx\" | grep -v node_modules); do
    apis=$(grep -o \"fetch(['\\"\`][^'\\"\`]*\" \"$f\" 2>/dev/null | head -20)
    if [ -n \"$apis\" ]; then
        echo \"$f:\"
        echo \"$apis\"
    fi
done
```

---

## STEP 3: BUILD THE MAPPING TABLE

Create `BACKEND_FRONTEND_MAP.md`:

```markdown
# Backend → Frontend Component Mapping

| # | Backend Source | Capability | API Route | Frontend Component | Status |
|---|---|---|---|---|---|
| 1 | server.py | Login | POST /api/auth/login | LoginPage.js | ✅ |
| 2 | server.py | Dashboard data | GET /api/dashboard | Dashboard.js | ✅ |
| 3 | live_state.py | Bot status | GET /api/bot/status | StatusBar.js | ✅ |
| 4 | live_state.py | Open positions | GET /api/positions | ??? | ❌ MISSING |
| 5 | backtest_engine.py | Run backtest | POST /api/backtest/run | ??? | ❌ MISSING |
| 6 | risk_calculator.py | Position size | GET /api/risk/calculate | ??? | ❌ MISSING |
| ... | ... | ... | ... | ... | ... |
```

**For EVERY row marked ❌ MISSING → you must create the component.**

---

## STEP 4: CREATE MISSING FRONTEND COMPONENTS

For each missing component, follow this template:

### Component Template

```jsx
import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '';

function ComponentName() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    const fetchData = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_URL}/api/endpoint`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setData(json);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => { fetchData(); }, []);
    
    // Auto-refresh for live data (every 5 seconds)
    useEffect(() => {
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);
    
    if (loading) return <div className=\"loading\">Loading...</div>;
    if (error) return <div className=\"error\">Error: {error}</div>;
    
    return (
        <div className=\"component-card\">
            <h3>Component Title</h3>
            {/* Render data here */}
            <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
    );
}

export default ComponentName;
```

---

## STEP 5: REQUIRED COMPONENTS (MUST CREATE IF MISSING)

### 5.1 — Bot Control Panel (live_state.py + orchestrator)
```
Buttons: Start Bot | Stop Bot | Emergency Stop | Restart
Display: Status (Running/Stopped), Uptime, Mode (Paper/Live)
API: POST /api/bot/start, POST /api/bot/stop, GET /api/bot/status
```

### 5.2 — Open Positions Panel (portfolio_manager.py + live_state.py)
```
Table: Symbol, Direction, Entry Price, Current Price, Unrealized P&L, Qty, SL, TP
Buttons: Close Position (per row), Close All
Auto-refresh: Every 3 seconds
API: GET /api/positions, POST /api/positions/close/{id}, POST /api/positions/close-all
```

### 5.3 — Active Orders Panel (broker_layer.py)
```
Table: Order ID, Symbol, Type (BUY/SELL), Price, Qty, Status (Pending/Filled/Cancelled)
Buttons: Cancel Order (per row), Cancel All
API: GET /api/orders, DELETE /api/orders/{id}
```

### 5.4 — Strategy Manager (strategy_selector.py + strategy_definitions.py)
```
Grid: All strategies with ON/OFF toggle
Each card shows: Name, Category, Win Rate, P&L, Status
Buttons: Enable All, Disable All, per-strategy toggle
API: GET /api/strategies/all, PUT /api/strategies/{name}/toggle
```

### 5.5 — Risk Dashboard (risk_guard.py + risk_calculator.py)
```
Display: Current risk %, Daily P&L, Daily loss limit remaining
Display: Max positions (current/max), Active risk per position
Indicators: Risk Guard status (Green/Yellow/Red)
Buttons: Edit risk limits
API: GET /api/risk/status, GET /api/risk/metrics, PUT /api/risk/limits
```

### 5.6 — Market Regime Widget (regime_gate.py + modules/regime/)
```
Display: Current regime (Trending Up/Down/Ranging/Volatile)
Display: Regime confidence %, last change time
Display: VIX value, VIX filter status
Color-coded badge
API: GET /api/regime/current
```

### 5.7 — Signal Feed (decision_engine.py + strategy_router.py)
```
Live feed: Last 50 signals generated
Each signal shows: Time, Strategy, Signal Type, Confidence, Taken/Rejected, Reason
Auto-refresh: Every 5 seconds
API: GET /api/signals/recent
```

### 5.8 — Backtest Runner (backtest_engine.py)
```
Form: Start date, End date, Strategies (multi-select), Capital, Risk %
Buttons: Run Backtest, Cancel, Download Results
Progress: Progress bar during execution
Results: Summary table + per-strategy breakdown
API: POST /api/backtest/run, GET /api/backtest/status, GET /api/backtest/results
```

### 5.9 — P&L Chart (reporting/equity_tracker.py)
```
Chart: Equity curve (daily P&L line chart)
Timeframes: 1D, 1W, 1M, 3M, 6M, All
Display: Total P&L, Win Rate, Profit Factor, Sharpe
API: GET /api/pnl/equity-curve?period=1M
```

### 5.10 — Trade Journal (MongoDB trade_journal)
```
Table: All trades with P&L, strategy, entry/exit, result
Detail modal: Click any trade for full details
Filters: Strategy, Date, Result, P&L range
Export: Download as CSV
API: GET /api/journal/trades, GET /api/journal/trade/{id}, GET /api/journal/export
```

### 5.11 — Indicator Panel (indicator_engine.py)
```
Display: Current values of key indicators (RSI, MACD, ATR, EMA, VWAP)
Per-symbol if multiple symbols
Auto-refresh: Every candle
API: GET /api/indicators/current?symbol=NIFTY
```

### 5.12 — Context Filters Status (modules/context_filters/)
```
Display: Status of each filter (Calendar, Chop, Gap, Time-of-Day)
Each shows: Active/Inactive, current value, threshold
API: GET /api/filters/status
```

### 5.13 — Alerts & Notifications (alert.py + notification_service.py)
```
Panel: Last 50 alerts/notifications
Each shows: Time, Type (Trade/Risk/System), Message, Severity
Button: Clear All, Mark Read
Settings: Toggle Telegram/Email/Push notifications
API: GET /api/alerts/recent, PUT /api/alerts/settings
```

### 5.14 — SMC Analysis Panel (modules/smc/)
```
Display: Detected Order Blocks, Fair Value Gaps, Liquidity Zones
Per-symbol: Show current structure analysis
API: GET /api/smc/analysis?symbol=NIFTY
```

### 5.15 — Config Editor (config/*.yaml)
```
Display: All YAML config files in a tabbed editor
Each tab = one config file
Editable: JSON/YAML editor with syntax highlighting
Save button per tab
API: GET /api/config/files, GET /api/config/{filename}, PUT /api/config/{filename}
```

### 5.16 — Logs Viewer (logs/)
```
Display: Last 500 lines of latest log file
Dropdown: Select log file
Auto-scroll: New lines appear at bottom
Button: Download full log
API: GET /api/logs/recent, GET /api/logs/files
```

### 5.17 — Manual Trade Entry
```
Form: Symbol, Direction (CE/PE), Quantity, Entry Price (or Market)
Optional: SL, TP, Strategy label
Button: Place Order
API: POST /api/manual/trade
```

### 5.18 — PA Engine Panel (Priceactionmdfiles integration)
```
Sub-tabs: PA Strategies, PA Edge Monitor, PA Monte Carlo, PA Backtest
Each reads from /api/pa/* endpoints (from GEMINI_UNIFIED_DASHBOARD.md)
```

### 5.19 — Capital & Risk Controls
```
Inputs: Capital (₹), Risk %, Max daily loss, Max positions
Sliders and number inputs
Save button → saves to all configs (root .env + PA config + paper_mode.yaml)
API: GET /api/config/capital, PUT /api/config/capital, etc.
```

### 5.20 — Daily Report Viewer (modules/reporting/)
```
Display: Today's report and historical reports
Shows: Trades taken, P&L, win/loss, strategies used, regime changes
Button: Generate report, Download PDF/CSV
API: GET /api/reports/today, GET /api/reports/history
```

---

## STEP 6: ADD MISSING API ROUTES TO server.py

For each frontend component that needs a route not yet in `server.py`, APPEND the route.

**Pattern for exposing a module's data:**

```python
# At the top of server.py, add import
sys.path.insert(0, os.path.join(ROOT_DIR))  # Root AlgoTrading Options dir

# Then at the bottom, add routes:

@app.get(\"/api/regime/current\")
def get_current_regime():
    try:
        from modules.regime_gate import RegimeGate
        # Or however the module exposes its state
        gate = RegimeGate.get_instance()  # or however it's accessed
        return {
            \"regime\": gate.current_regime,
            \"confidence\": gate.confidence,
            \"vix\": gate.vix_value,
        }
    except Exception as e:
        return {\"error\": str(e)}

@app.get(\"/api/risk/status\")
def get_risk_status():
    try:
        from modules.risk_guard import RiskGuard
        guard = RiskGuard.get_instance()
        return {
            \"daily_pnl\": guard.daily_pnl,
            \"daily_limit\": guard.daily_limit,
            \"open_positions\": guard.open_position_count,
            \"max_positions\": guard.max_positions,
            \"risk_per_trade\": guard.risk_per_trade,
            \"status\": \"GREEN\" if guard.can_trade() else \"RED\",
        }
    except Exception as e:
        return {\"error\": str(e)}

# ... Same pattern for every module
```

**IMPORTANT:** Don't instantiate modules that aren't already running. READ from existing state files, databases, or singleton instances. If the module isn't designed to be imported standalone, read from its OUTPUT files (JSON state files, logs, etc.) instead.

---

## STEP 7: WIRE INTO NAVIGATION

After all components are created, add them to the frontend navigation:

```jsx
// In App.js or your main router/navigation component
// ADD new tabs/pages for each new component

const TABS = [
    // Existing tabs (don't change)
    { name: 'Dashboard', component: Dashboard },
    { name: 'Trades', component: Trades },
    // ... existing ...
    
    // NEW TABS (add these)
    { name: 'Positions', component: OpenPositions },
    { name: 'Orders', component: ActiveOrders },
    { name: 'Strategy Manager', component: StrategyManager },
    { name: 'Risk', component: RiskDashboard },
    { name: 'Regime', component: RegimeWidget },
    { name: 'Signals', component: SignalFeed },
    { name: 'Backtest', component: BacktestRunner },
    { name: 'P&L Chart', component: PnLChart },
    { name: 'Journal', component: TradeJournal },
    { name: 'Indicators', component: IndicatorPanel },
    { name: 'Filters', component: FilterStatus },
    { name: 'Alerts', component: AlertsPanel },
    { name: 'SMC', component: SMCPanel },
    { name: 'Config', component: ConfigEditor },
    { name: 'Logs', component: LogViewer },
    { name: 'Manual Trade', component: ManualTrade },
    { name: 'PA Engine', component: PAEnginePanel },
    { name: 'Reports', component: DailyReport },
    { name: 'Capital', component: CapitalRiskControls },
];
```

If the navigation is a sidebar, add entries. If it's tabs, add tabs. Match the existing UI pattern.

---

## STEP 8: VERIFY COMPLETENESS

After building everything, create the final verification:

```bash
# Count backend routes
echo \"Backend routes:\" 
grep -c \"@app\.\" AlgoTradingTelegramBotAndFrontend/backend/server.py

# Count frontend components
echo \"Frontend components:\"
find AlgoTradingTelegramBotAndFrontend/frontend/src -name \"*.js\" -o -name \"*.jsx\" | grep -v node_modules | wc -l

# Count API calls in frontend
echo \"Frontend API calls:\"
grep -r \"fetch(\" AlgoTradingTelegramBotAndFrontend/frontend/src --include=\"*.js\" --include=\"*.jsx\" | grep -v node_modules | wc -l
```

**Create `COMPLETENESS_REPORT.md`:**

```markdown
| Backend Capability | API Route | Frontend Component | Clickable | Viewable | Save Works |
|---|---|---|---|---|---|
| Bot Start/Stop | POST /api/bot/start | BotControl.js | ✅ | ✅ | N/A |
| Open Positions | GET /api/positions | Positions.js | ✅ | ✅ | N/A |
| ... (every single one) | ... | ... | ... | ... | ... |

TOTAL:
  Backend capabilities: XX
  Frontend components: XX
  Coverage: 100%
```

---

## RULES

1. **DO NOT change any backend logic** — only ADD routes that expose existing data
2. **DO NOT change any module logic** — only READ from their state/output
3. **Every new route** reads from existing data sources (files, DB, module state)
4. **Every new component** calls an API and renders data
5. **Every interactive element** (button, toggle, input) calls an API that writes to config
6. **If a module can't be imported standalone**, read from its output files instead
7. **Match the existing UI style** — use the same CSS classes, layout, color scheme

## START WITH STEP 1. Map every backend route. THEN check frontend coverage. THEN build what's missing. GO.
"
Observation: Create successful: /app/frontend_fixes/07_BACKEND_FRONTEND_COMPLETENESS.md