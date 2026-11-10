Now I have the full picture. Your project is massive and well-structured. Let me write the updated prompt:
Action: file_editor create /app/GEMINI_UNIFIED_DASHBOARD.md --file-text "# CONNECT EVERYTHING — Unified Internal Wiring
## Link Price Action Strategy Engine → Live Trader → Dashboard Frontend
### STRICTLY NO LOGIC CHANGES — Only add connection wiring

---

## YOUR ACTUAL PROJECT STRUCTURE

```
C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\          ← ROOT (Live Trader)
│
├── main.py / orchestrator.py / run_live.py                   ← Live entry points
├── live_options_trader.py / live_trader_v3.py                ← Live traders
├── backtest_engine.py                                        ← Root backtest engine
├── .env                                                      ← Root config
│
├── modules/                                                  ← CORE ENGINE (35+ modules)
│   ├── price_action_engine.py          ← Price action detection
│   ├── decision_engine.py              ← Trade decision maker
│   ├── strategy_selector.py            ← Strategy selection
│   ├── strategy_router.py              ← Routes signals to strategies
│   ├── strategy_definitions.py         ← Strategy configs
│   ├── candlestick_engine.py           ← Candlestick patterns
│   ├── momentum_engine.py              ← Momentum strategies
│   ├── mean_reversion_engine.py        ← Mean reversion
│   ├── structure_strategy_engine.py    ← Market structure
│   ├── sweep_retest_engine.py          ← Sweep & retest
│   ├── broker_layer.py                 ← Broker connection (Zerodha/Angel)
│   ├── risk_guard.py                   ← Risk management
│   ├── trailing_sl_manager.py          ← Trailing stop loss
│   ├── regime_gate.py                  ← Market regime filter
│   ├── indicator_engine.py             ← Technical indicators
│   ├── dashboard_bridge.py             ← EXISTING bridge to dashboard
│   ├── websocket_manager.py            ← Live data feed
│   ├── portfolio_manager.py            ← Portfolio tracking
│   ├── confidence_scorer.py            ← Signal confidence
│   ├── context_detector.py             ← Market context
│   ├── data_layer.py                   ← Data access
│   ├── option_chain.py                 ← Options chain
│   ├── vix_filter.py                   ← VIX-based filtering
│   │
│   ├── broker/ (binance_broker.py)
│   ├── charting/ (aggregator, chart_renderer, structure_detector)
│   ├── context_filters/ (calendar, chop, gap, time_of_day)
│   ├── data/ (binance_feed, candle_builder, websocket_feed)
│   ├── intermarket/ (breadth, cross_asset, sector_strength)
│   ├── options/ (broker_adapter, risk_manager, strike_selector, trade_executor)
│   ├── regime/ (classifier, hmm_layer, rule_layer)
│   ├── reporting/ (daily_report, equity_tracker)
│   ├── risk_exec/ (breaker, engine, executor, exits, sizer, trailing)
│   ├── smc/ (engine, fair_value_gap, liquidity_sweep, order_block, structure)
│   └── vp_avwap/ (anchored_vwap, session_profile, volume_profile)
│
├── config/                                                   ← YAML configs (25+ files)
│   ├── momentum.yaml, regime.yaml, risk_execution.yaml
│   ├── smc.yaml, trailing_sl.yaml, vix_filter.yaml
│   ├── candlestick.yaml, context_filters.yaml
│   └── paper_mode.yaml, portfolio_limits.yaml
│
├── dashboard/                                                ← EXISTING DASHBOARD BACKEND
│   ├── app.py, charts.py, loader.py
│   └── data/ (backtest results JSONs, equity state, walk-forward results)
│
├── data/                                                     ← Historical data
├── logs/                                                     ← Trading logs
├── reports/                                                  ← Backtest reports
│
├── Priceactionmdfiles/                                       ← PRICE ACTION ENGINE (from pipeline)
│   ├── engine/
│   │   ├── unified_strategy_engine.py
│   │   ├── signal.py, base_strategy.py
│   │   ├── strategy_engine.py, strategy_selector.py, strategy_registry.py
│   │   ├── advanced_concepts/ (9 strategies)
│   │   ├── candlestick_patterns/ (11 strategies)
│   │   ├── price_action_patterns/ (19 strategies)
│   │   └── support_resistance/ (9 strategies)
│   ├── edge_monitor.py
│   ├── massive_backtest.py
│   ├── pipeline/
│   │   ├── results/
│   │   │   ├── FINAL_PRODUCTION_CONFIG.json     ← THE CONFIG
│   │   │   ├── monte_carlo_results.json
│   │   │   └── phase1-6 CSVs
│   │   ├── 01-05 python scripts
│   └── data/ (OHLCV CSVs)
│
└── AlgoTradingTelegramBotAndFrontend/                        ← FRONTEND APP
    ├── backend/
    │   ├── server.py                   ← FastAPI backend for React frontend
    │   ├── backtest_engine.py          ← Dashboard backtest engine
    │   ├── live_state.py               ← Live state reader
    │   ├── risk_calculator.py          ← Risk calculator
    │   ├── notification_service.py     ← Alert service
    │   └── .env
    └── frontend/
        ├── src/                        ← React source (your existing frontend)
        ├── build/                      ← Production build
        ├── package.json
        └── .env
```

---

## WHAT NEEDS TO HAPPEN (Connection Map)

```
EXISTING CONNECTIONS (Don't touch):
  modules/broker_layer.py ──→ Zerodha/Angel API
  modules/websocket_manager.py ──→ Live market data
  modules/dashboard_bridge.py ──→ dashboard/app.py
  AlgoTradingTelegramBotAndFrontend/backend/server.py ──→ frontend React app

NEW CONNECTIONS NEEDED (Add wiring only):
  ┌─────────────────────────────────────────────────┐
  │ Priceactionmdfiles/engine/ (48 strategies)       │
  │   ↓ NEW IMPORT BRIDGE                           │
  │ modules/price_action_engine.py (existing module) │
  │   ↓ ALREADY CONNECTED                           │
  │ modules/decision_engine.py                       │
  │   ↓ ALREADY CONNECTED                           │
  │ orchestrator.py → live trading                   │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ Priceactionmdfiles/pipeline/results/             │
  │   ↓ NEW API ENDPOINT                            │
  │ AlgoTradingTelegramBotAndFrontend/backend/       │
  │   ↓ ALREADY CONNECTED                           │
  │ React Frontend (backtest view, config editor)    │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ Priceactionmdfiles/edge_monitor.py               │
  │   ↓ NEW API ENDPOINT                            │
  │ AlgoTradingTelegramBotAndFrontend/backend/       │
  │   ↓ ALREADY CONNECTED                           │
  │ React Frontend (edge monitor tab)                │
  └─────────────────────────────────────────────────┘
```

---

## STEP 1: CREATE THE BRIDGE FILE

**Create NEW file:** `modules/pa_engine_bridge.py`

This is the ONLY new file in modules/. It imports from Priceactionmdfiles/engine/ and exposes it in the format that modules/price_action_engine.py already uses.

```python
\"\"\"
PA Engine Bridge — Connects Priceactionmdfiles/engine to modules/
=================================================================

This bridge imports the 48-strategy engine from Priceactionmdfiles
and exposes signals in the format the existing decision_engine expects.

DOES NOT CHANGE ANY EXISTING CODE. Only bridges the two systems.
\"\"\"

import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

# Add Priceactionmdfiles to path
PA_ENGINE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    \"Priceactionmdfiles\"
)
if PA_ENGINE_DIR not in sys.path:
    sys.path.insert(0, PA_ENGINE_DIR)

# Load production config
CONFIG_PATH = os.path.join(PA_ENGINE_DIR, \"pipeline\", \"results\", \"FINAL_PRODUCTION_CONFIG.json\")


class PAEngineBridge:
    \"\"\"Bridge between Priceactionmdfiles engine and the live trader modules.\"\"\"
    
    _engine = None
    _config = None
    _edge_monitor = None
    
    @classmethod
    def get_engine(cls):
        \"\"\"Lazy-load the unified strategy engine.\"\"\"
        if cls._engine is None:
            try:
                from engine.unified_strategy_engine import UnifiedStrategyEngine
                cls._engine = UnifiedStrategyEngine()
                logger.info(f\"PA Engine loaded from {PA_ENGINE_DIR}\")
            except ImportError as e:
                logger.error(f\"Failed to import PA engine: {e}\")
                return None
        return cls._engine
    
    @classmethod
    def get_config(cls):
        \"\"\"Load FINAL_PRODUCTION_CONFIG.json.\"\"\"
        if cls._config is None:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    cls._config = json.load(f)
                logger.info(f\"PA config loaded: {len(cls._config.get('strategies', []))} strategies\")
            else:
                logger.warning(f\"PA config not found at {CONFIG_PATH}\")
                cls._config = {}
        return cls._config
    
    @classmethod
    def save_config(cls, config: dict):
        \"\"\"Save updated config (from frontend edits).\"\"\"
        import shutil
        if os.path.exists(CONFIG_PATH):
            shutil.copy2(CONFIG_PATH, CONFIG_PATH + '.backup')
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        cls._config = config
        logger.info(\"PA config saved\")
    
    @classmethod
    def get_signals(cls, df, timeframe='5m'):
        \"\"\"
        Get signals from the 48-strategy PA engine.
        
        Args:
            df: OHLCV DataFrame (columns: open, high, low, close, volume)
            timeframe: '5m', '15m', etc.
        
        Returns:
            List of dicts in the format the existing decision_engine expects:
            [
                {
                    'strategy': 'Breakout-Retest-Continuation',
                    'signal': 'BUY',
                    'confidence': 0.85,
                    'source': 'pa_engine',
                    'entry_price': 23450.5,
                    'stop_loss': 23400.0,
                    'take_profit': 23550.0,
                }
            ]
        \"\"\"
        engine = cls.get_engine()
        config = cls.get_config()
        
        if engine is None:
            return []
        
        try:
            raw_signals = engine.get_signals(df, backtest_mode=False)
            if not raw_signals:
                return []
            
            # Filter by production config
            active_strategies = set(config.get('strategies', []))
            allowed_hours = set(config.get('allowed_hours', []))
            
            filtered = []
            for sig in raw_signals:
                # Strategy filter
                if active_strategies and sig.strategy_name not in active_strategies:
                    continue
                
                # Confidence filter
                strat_cfg = config.get('strategy_configs', {}).get(sig.strategy_name, {})
                min_conf = strat_cfg.get('optimal_confidence', 0.70)
                if sig.confidence < min_conf:
                    continue
                
                # Convert to the format decision_engine expects
                filtered.append({
                    'strategy': sig.strategy_name,
                    'signal': sig.signal_type.value if hasattr(sig.signal_type, 'value') else str(sig.signal_type),
                    'confidence': sig.confidence,
                    'source': 'pa_engine',
                    'entry_price': getattr(sig, 'entry_price', None),
                    'stop_loss': getattr(sig, 'stop_loss', None),
                    'take_profit': getattr(sig, 'take_profit', None),
                    'metadata': getattr(sig, 'metadata', {}),
                })
            
            return filtered
            
        except Exception as e:
            logger.error(f\"PA engine signal error: {e}\")
            return []
    
    @classmethod
    def get_edge_status(cls):
        \"\"\"Run edge monitor and return status.\"\"\"
        try:
            from edge_monitor import EdgeMonitor
            
            # Find the most recent backtest CSV
            results_dir = os.path.join(PA_ENGINE_DIR, \"pipeline\", \"results\")
            csv_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
            if not csv_files:
                return {\"status\": \"NO_DATA\", \"is_alive\": True}
            
            latest_csv = os.path.join(results_dir, sorted(csv_files)[-1])
            monitor = EdgeMonitor(trades_csv=latest_csv, capital=500000)
            
            return {
                \"status\": \"GREEN\" if monitor.is_edge_alive() else \"RED\",
                \"is_alive\": monitor.is_edge_alive(),
                \"triggers\": monitor.generate_stop_triggers(),
                \"kelly\": monitor.kelly_criterion(),
                \"decay\": monitor.rolling_edge_decay(),
                \"streaks\": monitor.consecutive_loss_analysis(),
            }
        except Exception as e:
            logger.error(f\"Edge monitor error: {e}\")
            return {\"status\": \"ERROR\", \"error\": str(e), \"is_alive\": True}
    
    @classmethod
    def get_monte_carlo(cls):
        \"\"\"Read Monte Carlo results.\"\"\"
        mc_path = os.path.join(PA_ENGINE_DIR, \"pipeline\", \"results\", \"monte_carlo_results.json\")
        if os.path.exists(mc_path):
            with open(mc_path, 'r') as f:
                return json.load(f)
        return None
    
    @classmethod
    def get_backtest_results(cls):
        \"\"\"List all backtest result files.\"\"\"
        results_dir = os.path.join(PA_ENGINE_DIR, \"pipeline\", \"results\")
        files = []
        if os.path.exists(results_dir):
            for f in sorted(os.listdir(results_dir)):
                path = os.path.join(results_dir, f)
                files.append({
                    \"name\": f,
                    \"type\": f.split('.')[-1],
                    \"size_kb\": round(os.path.getsize(path) / 1024, 1),
                })
        return files
```

---

## STEP 2: WIRE INTO modules/price_action_engine.py

**DO NOT REWRITE** `price_action_engine.py`. Only ADD the bridge import at the end of the file or wherever signals are gathered.

Find the method in `price_action_engine.py` that generates/returns signals. At the point where it returns signals, ADD a merge step:

```python
# ADD this import at the top of price_action_engine.py
try:
    from modules.pa_engine_bridge import PAEngineBridge
    PA_BRIDGE_AVAILABLE = True
except ImportError:
    PA_BRIDGE_AVAILABLE = False

# Then, in the method that returns signals (e.g., analyze(), get_signals(), scan()):
# AFTER the existing signal generation logic, ADD:

if PA_BRIDGE_AVAILABLE:
    try:
        pa_signals = PAEngineBridge.get_signals(df, timeframe=timeframe)
        # Merge PA signals with existing signals
        # PA signals have 'source': 'pa_engine' so they're distinguishable
        all_signals.extend(pa_signals)  # or however signals are aggregated
    except Exception as e:
        logger.warning(f\"PA bridge signal fetch failed: {e}\")
```

**IMPORTANT:** Read the actual `price_action_engine.py` first to understand its signal format. The bridge output MUST match that format exactly. Adjust the dict keys in `PAEngineBridge.get_signals()` to match.

---

## STEP 3: WIRE INTO AlgoTradingTelegramBotAndFrontend/backend/server.py

**DO NOT REWRITE** `server.py`. ADD new API routes at the bottom of the file for the PA engine features:

```python
# ADD at the top of server.py
import sys, os
PA_ENGINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), \"Priceactionmdfiles\")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, PA_ENGINE_DIR)

try:
    from modules.pa_engine_bridge import PAEngineBridge
    PA_AVAILABLE = True
except:
    PA_AVAILABLE = False

# ============================================================
# ADD these new routes at the BOTTOM of server.py
# (Don't modify any existing routes above)
# ============================================================

# --- PA ENGINE CONFIG ---
@app.get(\"/api/pa/config\")
def get_pa_config():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    return PAEngineBridge.get_config()

@app.put(\"/api/pa/config\")
async def save_pa_config(request: Request):
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    data = await request.json()
    PAEngineBridge.save_config(data)
    return {\"status\": \"saved\"}

# --- PA STRATEGIES ---
@app.get(\"/api/pa/strategies\")
def get_pa_strategies():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    config = PAEngineBridge.get_config()
    active = set(config.get(\"strategies\", []))
    all_configs = config.get(\"strategy_configs\", {})
    strategies = []
    for name, cfg in all_configs.items():
        strategies.append({
            \"name\": name, \"active\": name in active,
            \"confidence\": cfg.get(\"optimal_confidence\", 0),
            \"profit_factor\": cfg.get(\"profit_factor_at_threshold\", 0),
            \"direction\": cfg.get(\"preferred_direction\", \"ANY\"),
            \"regimes\": cfg.get(\"allowed_regimes\", []),
        })
    return sorted(strategies, key=lambda x: x['profit_factor'], reverse=True)

@app.put(\"/api/pa/strategies/{name}/toggle\")
def toggle_pa_strategy(name: str):
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    config = PAEngineBridge.get_config()
    strategies = config.get(\"strategies\", [])
    if name in strategies:
        strategies.remove(name); action = \"disabled\"
    else:
        strategies.append(name); action = \"enabled\"
    config[\"strategies\"] = strategies
    PAEngineBridge.save_config(config)
    return {\"strategy\": name, \"action\": action}

# --- PA EDGE MONITOR ---
@app.get(\"/api/pa/edge\")
def get_pa_edge():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    return PAEngineBridge.get_edge_status()

# --- PA MONTE CARLO ---
@app.get(\"/api/pa/montecarlo\")
def get_pa_monte_carlo():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    return PAEngineBridge.get_monte_carlo() or {\"error\": \"No MC results\"}

# --- PA BACKTEST RESULTS ---
@app.get(\"/api/pa/backtest/files\")
def get_pa_backtest_files():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    return PAEngineBridge.get_backtest_results()

@app.get(\"/api/pa/backtest/{filename}\")
def get_pa_backtest_file(filename: str):
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    import pandas as pd
    path = os.path.join(PA_ENGINE_DIR, \"pipeline\", \"results\", filename)
    if not os.path.exists(path): return {\"error\": \"File not found\"}
    if filename.endswith('.csv'):
        df = pd.read_csv(path)
        return {\"data\": df.tail(1000).to_dict(orient='records'), \"total\": len(df)}
    elif filename.endswith('.json'):
        import json
        with open(path) as f: return json.load(f)
    else:
        with open(path) as f: return {\"content\": f.read()}

# --- PA SCHEDULE/RISK SETTINGS ---
@app.get(\"/api/pa/schedule\")
def get_pa_schedule():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    config = PAEngineBridge.get_config()
    return {
        \"allowed_hours\": config.get(\"allowed_hours\", []),
        \"allowed_days\": config.get(\"allowed_days\", []),
        \"sl_method\": config.get(\"sl_method\", \"\"),
    }

@app.put(\"/api/pa/schedule\")
async def save_pa_schedule(request: Request):
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    data = await request.json()
    config = PAEngineBridge.get_config()
    if \"allowed_hours\" in data: config[\"allowed_hours\"] = data[\"allowed_hours\"]
    if \"allowed_days\" in data: config[\"allowed_days\"] = data[\"allowed_days\"]
    if \"sl_method\" in data: config[\"sl_method\"] = data[\"sl_method\"]
    PAEngineBridge.save_config(config)
    return {\"status\": \"saved\"}

@app.get(\"/api/pa/risk\")
def get_pa_risk():
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    return PAEngineBridge.get_config().get(\"risk_management\", {})

@app.put(\"/api/pa/risk\")
async def save_pa_risk(request: Request):
    if not PA_AVAILABLE: return {\"error\": \"PA engine not available\"}
    data = await request.json()
    config = PAEngineBridge.get_config()
    config[\"risk_management\"] = data
    PAEngineBridge.save_config(config)
    return {\"status\": \"saved\"}
```

---

## STEP 4: ADD FRONTEND TABS (React)

**DO NOT REWRITE** any existing React components. ADD new components alongside them.

In the React frontend, add these new tabs/pages that call the new `/api/pa/*` endpoints:

### Tab: PA Strategy Manager
```
GET /api/pa/strategies → Show all 48 strategies with toggle switches
PUT /api/pa/strategies/{name}/toggle → Toggle on/off
Each strategy shows: name, PF, confidence, direction, regimes, active status
SAVE: Changes auto-save via toggle (instant PUT calls)
```

### Tab: PA Config Editor
```
GET /api/pa/config → Load full config
GET /api/pa/schedule → Load hours/days/SL
GET /api/pa/risk → Load risk settings

Editable fields:
- Capital (₹ input)
- Risk % (slider 0.25-3.0)
- Allowed hours (checkbox grid: 9-15)
- Allowed days (checkbox: Mon-Fri)
- SL Method (dropdown: FIXED_2R, FIXED_3R, TRAIL_1.5ATR, TRAIL_2ATR, TRAIL_2.5ATR)
- Max loss/trade, Max daily loss, Max weekly loss (₹ inputs)
- Max concurrent positions (number input)
- Max consecutive losses before pause (number input)

SAVE button → PUT /api/pa/schedule + PUT /api/pa/risk + PUT /api/pa/config
Show toast: \"Config saved successfully (backup created)\"
```

### Tab: PA Edge Monitor
```
GET /api/pa/edge → Show edge status
Display:
  - STATUS badge: GREEN / YELLOW / RED
  - Kelly criterion: recommended risk %
  - Decay analysis: improving / stable / weakening
  - Loss streak: current and max
  - Stop triggers: which are active
  - Full report text

SAVE: Export edge report as .txt download
```

### Tab: PA Monte Carlo
```
GET /api/pa/montecarlo → Show simulation results
Display:
  - Probability table (profit, 70% ROI, double, ruin)
  - Capital distribution (percentiles)
  - Drawdown stats
  - Kelly optimization table
  
SAVE: Export MC report as .txt download
```

### Tab: PA Backtest Results
```
GET /api/pa/backtest/files → List all CSVs/JSONs
GET /api/pa/backtest/{filename} → Load specific file
Display:
  - Dropdown to select file
  - Data table with sorting
  - Summary stats (if CSV with pnl column)
  
SAVE: Download selected file as CSV
```

---

## STEP 5: SAVE BUTTONS ON EVERY EXISTING TAB

For each EXISTING tab that shows configuration or data, add a save mechanism:

```javascript
// Generic save handler for any tab
async function saveToBackend(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        showToast(result.status === 'saved' ? 'Saved successfully!' : 'Save failed: ' + result.error);
    } catch (err) {
        showToast('Save error: ' + err.message, 'error');
    }
}

// Save button component
function SaveButton({ onClick, label = \"Save\" }) {
    return <button onClick={onClick} className=\"save-btn\">{label}</button>;
}
```

**Every tab must have:**
1. A \"Save\" button in the top-right corner
2. On click → calls the corresponding PUT endpoint
3. Shows success/failure toast
4. Backend writes to the actual JSON/YAML file on disk

---

## STEP 6: VERIFY CONNECTIONS

After building, verify with these curl commands:

```bash
# Health check
curl http://localhost:PORT/api/pa/config
curl http://localhost:PORT/api/pa/strategies
curl http://localhost:PORT/api/pa/edge
curl http://localhost:PORT/api/pa/montecarlo
curl http://localhost:PORT/api/pa/backtest/files
curl http://localhost:PORT/api/pa/schedule
curl http://localhost:PORT/api/pa/risk

# Save test (config edit)
curl -X PUT http://localhost:PORT/api/pa/schedule \
  -H \"Content-Type: application/json\" \
  -d '{\"allowed_hours\":[10,11],\"allowed_days\":[\"Thursday\",\"Friday\"]}'

# Strategy toggle
curl -X PUT http://localhost:PORT/api/pa/strategies/Market%20Structure/toggle

# Verify it saved
curl http://localhost:PORT/api/pa/config | python -m json.tool | head -20
```

---

## FILES TO CREATE (New files only)

```
modules/pa_engine_bridge.py           ← THE BRIDGE (Step 1)
```

## FILES TO EDIT (Append only, don't rewrite)

```
modules/price_action_engine.py        ← Add 5 lines: import bridge + merge signals (Step 2)
AlgoTradingTelegramBotAndFrontend/backend/server.py  ← Append ~80 lines of new routes (Step 3)
AlgoTradingTelegramBotAndFrontend/frontend/src/       ← Add 5 new components (Step 4-5)
```

## FILES NOT TO TOUCH

```
EVERYTHING ELSE. Especially:
- main.py, orchestrator.py, run_live.py
- modules/decision_engine.py
- modules/strategy_selector.py
- modules/broker_layer.py
- modules/risk_guard.py
- All files in config/
- All files in Priceactionmdfiles/engine/
- All files in Priceactionmdfiles/pipeline/
- edge_monitor.py, massive_backtest.py
- backtest_engine.py (root)
```

---

## CRITICAL RULES

1. **DO NOT modify any existing logic.** Only ADD bridge code and API routes.
2. **DO NOT change signal format** in existing modules. The bridge adapts to match.
3. **DO NOT move files.** The bridge uses `sys.path` to import across directories.
4. **DO NOT change config/\*.yaml files.** PA config lives in its own JSON.
5. **Every frontend save → backend API → writes to actual file on disk.**
6. **If import fails (PA engine not found), fail gracefully** — existing system works without it.
7. **Read `modules/price_action_engine.py` FIRST** to understand its signal format before writing the bridge adapter.
8. **Read `AlgoTradingTelegramBotAndFrontend/backend/server.py` FIRST** to understand existing routes before appending new ones.

## START BY READING THE TWO KEY FILES. THEN BUILD THE BRIDGE. THEN ADD ROUTES. THEN FRONTEND. GO.
"
Observation: Overwrite successful: /app/GEMINI_UNIFIED_DASHBOARD.md