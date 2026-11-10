
Action: file_editor create /app/frontend_fixes/03_ENABLE_CONFIG_CONTROLS.md --file-text "# 03 — ENABLE CAPITAL, RISK%, AND STRATEGY CONTROLS
## Make every configuration editable from the frontend with instant save

---

## MISSION

Enable these controls in the frontend dashboard:
1. **Capital** — Editable ₹ amount, saves to config
2. **Risk %** — Slider or input, saves to config
3. **Strategy toggles** — ON/OFF for each strategy (backtest + manual trades)
4. **SL Method** — Dropdown selection
5. **Trading hours** — Checkbox grid
6. **Trading days** — Checkbox group
7. **Risk limits** — Max loss per trade, daily, weekly, concurrent positions

**Every change MUST save to the backend immediately AND reflect in the live trading config.**

---

## STEP 1: FIND EXISTING CONFIG UI

First, search the frontend for existing config-related components:

```bash
find AlgoTradingTelegramBotAndFrontend/frontend/src -name \"*.js\" -o -name \"*.jsx\" | xargs grep -l \"capital\|risk\|strateg\|config\|setting\" | sort
```

Check if these components already exist but are hidden/disabled:
```bash
grep -rn \"disabled\|hidden\|display.*none\|visibility.*hidden\" AlgoTradingTelegramBotAndFrontend/frontend/src/ --include=\"*.js\" | grep -i \"capital\|risk\|config\"
```

---

## STEP 2: CAPITAL CONTROL

### Backend (append to server.py if not exists):

```python
@app.get(\"/api/config/capital\")
def get_capital():
    # Read from your existing config source
    # Could be .env, config.json, paper_mode.yaml, or MongoDB
    config = load_current_config()  # Use whatever existing config loader you have
    return {\"capital\": config.get(\"capital\", 500000)}

@app.put(\"/api/config/capital\")
async def set_capital(request: Request):
    data = await request.json()
    capital = data.get(\"capital\")
    if not capital or capital < 10000:
        return {\"error\": \"Capital must be at least ₹10,000\"}
    
    # Save to your existing config system
    update_config(\"capital\", capital)
    
    # Also update PA engine config if connected
    try:
        from modules.pa_engine_bridge import PAEngineBridge
        config = PAEngineBridge.get_config()
        config[\"capital\"] = capital
        PAEngineBridge.save_config(config)
    except: pass
    
    return {\"status\": \"saved\", \"capital\": capital}
```

### Frontend component:

```jsx
function CapitalControl() {
    const [capital, setCapital] = useState(500000);
    const [editing, setEditing] = useState(false);
    
    useEffect(() => {
        fetch(`${API_URL}/api/config/capital`)
            .then(r => r.json())
            .then(d => setCapital(d.capital));
    }, []);
    
    const saveCapital = async () => {
        const res = await fetch(`${API_URL}/api/config/capital`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ capital })
        });
        const data = await res.json();
        if (data.status === 'saved') {
            toast.success(`Capital set to ₹${capital.toLocaleString()}`);
            setEditing(false);
        }
    };
    
    return (
        <div className=\"config-control\">
            <label>Trading Capital</label>
            {editing ? (
                <>
                    <input type=\"number\" value={capital} 
                           onChange={e => setCapital(Number(e.target.value))}
                           min={10000} step={10000} />
                    <button onClick={saveCapital}>Save</button>
                    <button onClick={() => setEditing(false)}>Cancel</button>
                </>
            ) : (
                <>
                    <span>₹{capital.toLocaleString()}</span>
                    <button onClick={() => setEditing(true)}>Edit</button>
                </>
            )}
        </div>
    );
}
```

---

## STEP 3: RISK % CONTROL

### Backend:

```python
@app.get(\"/api/config/risk\")
def get_risk_pct():
    config = load_current_config()
    return {\"risk_pct\": config.get(\"risk_pct\", 1.0)}

@app.put(\"/api/config/risk\")
async def set_risk_pct(request: Request):
    data = await request.json()
    risk = data.get(\"risk_pct\")
    if risk < 0.1 or risk > 5.0:
        return {\"error\": \"Risk must be between 0.1% and 5.0%\"}
    update_config(\"risk_pct\", risk)
    return {\"status\": \"saved\", \"risk_pct\": risk}
```

### Frontend:

```jsx
function RiskControl() {
    const [risk, setRisk] = useState(1.0);
    
    const saveRisk = async () => {
        await fetch(`${API_URL}/api/config/risk`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ risk_pct: risk })
        });
        toast.success(`Risk set to ${risk}%`);
    };
    
    return (
        <div className=\"config-control\">
            <label>Risk per Trade: {risk}%</label>
            <input type=\"range\" min={0.25} max={3.0} step={0.25}
                   value={risk} onChange={e => setRisk(Number(e.target.value))} />
            <span>₹{(500000 * risk / 100).toLocaleString()} per trade</span>
            <button onClick={saveRisk}>Save</button>
        </div>
    );
}
```

---

## STEP 4: STRATEGY TOGGLE GRID

### Backend:

```python
@app.get(\"/api/strategies/all\")
def get_all_strategies():
    \"\"\"Return ALL strategies with their active/inactive status.\"\"\"
    # Read from FINAL_PRODUCTION_CONFIG.json
    # AND from existing strategy_definitions/strategy_filter config
    all_strategies = get_all_available_strategies()  # From modules or config
    active = get_active_strategies()  # From current config
    
    result = []
    for name, info in all_strategies.items():
        result.append({
            \"name\": name,
            \"active\": name in active,
            \"category\": info.get(\"category\", \"\"),
            \"backtest_enabled\": info.get(\"backtest_enabled\", True),
            \"manual_enabled\": info.get(\"manual_enabled\", True),
        })
    return result

@app.put(\"/api/strategies/{name}/toggle\")
def toggle_strategy(name: str, request: Request):
    data = request.json()
    mode = data.get(\"mode\", \"both\")  # \"backtest\", \"manual\", or \"both\"
    
    config = load_current_config()
    strategies = config.get(\"active_strategies\", [])
    
    if name in strategies:
        strategies.remove(name)
        action = \"disabled\"
    else:
        strategies.append(name)
        action = \"enabled\"
    
    config[\"active_strategies\"] = strategies
    save_config(config)
    
    return {\"strategy\": name, \"action\": action, \"mode\": mode}

@app.put(\"/api/strategies/batch\")
async def batch_toggle_strategies(request: Request):
    \"\"\"Enable/disable multiple strategies at once.\"\"\"
    data = await request.json()
    strategies = data.get(\"strategies\", [])
    action = data.get(\"action\", \"enable\")  # \"enable\" or \"disable\"
    
    config = load_current_config()
    active = set(config.get(\"active_strategies\", []))
    
    if action == \"enable\":
        active.update(strategies)
    else:
        active -= set(strategies)
    
    config[\"active_strategies\"] = list(active)
    save_config(config)
    
    return {\"status\": \"saved\", \"active_count\": len(active)}
```

### Frontend:

```jsx
function StrategyGrid() {
    const [strategies, setStrategies] = useState([]);
    
    useEffect(() => {
        fetch(`${API_URL}/api/strategies/all`)
            .then(r => r.json())
            .then(setStrategies);
    }, []);
    
    const toggle = async (name) => {
        await fetch(`${API_URL}/api/strategies/${encodeURIComponent(name)}/toggle`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'both' })
        });
        // Refresh
        const res = await fetch(`${API_URL}/api/strategies/all`);
        setStrategies(await res.json());
    };
    
    const enableAll = async () => {
        const names = strategies.map(s => s.name);
        await fetch(`${API_URL}/api/strategies/batch`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ strategies: names, action: 'enable' })
        });
        const res = await fetch(`${API_URL}/api/strategies/all`);
        setStrategies(await res.json());
        toast.success('All strategies enabled');
    };
    
    return (
        <div>
            <div className=\"strategy-actions\">
                <button onClick={enableAll}>Enable All</button>
                <button onClick={disableAll}>Disable All</button>
            </div>
            <div className=\"strategy-grid\">
                {strategies.map(s => (
                    <div key={s.name} className={`strategy-card ${s.active ? 'active' : 'inactive'}`}>
                        <span>{s.name}</span>
                        <span>{s.category}</span>
                        <label className=\"switch\">
                            <input type=\"checkbox\" checked={s.active} onChange={() => toggle(s.name)} />
                            <span className=\"slider\"></span>
                        </label>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

---

## STEP 5: TRADING SCHEDULE CONTROLS

```jsx
function ScheduleControl() {
    const hours = [9, 10, 11, 12, 13, 14, 15];
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const slMethods = ['FIXED_2R', 'FIXED_3R', 'TRAIL_1.5ATR', 'TRAIL_2ATR', 'TRAIL_2.5ATR'];
    
    const [schedule, setSchedule] = useState({ allowed_hours: [], allowed_days: [], sl_method: '' });
    
    // Load, toggle hours/days, save — same pattern as above
    // Every checkbox change → immediate PUT to /api/config/schedule or /api/pa/schedule
}
```

---

## STEP 6: RISK LIMITS PANEL

```jsx
function RiskLimits() {
    const [limits, setLimits] = useState({
        max_loss_per_trade: 5000,
        max_daily_loss: 25000,
        max_weekly_loss: 50000,
        max_concurrent_positions: 3,
        max_consecutive_losses_before_pause: 8,
    });
    
    // Editable inputs for each field
    // Save button → PUT /api/config/risk-limits or /api/pa/risk
}
```

---

## VALIDATION

After building, test:
```
[ ] Capital change → saved → reload page → value persists
[ ] Risk % change → saved → reload → persists
[ ] Strategy toggle → saved → reload → state persists
[ ] Enable all / Disable all → works
[ ] Schedule change → saved → persists
[ ] Risk limits → saved → persists
[ ] All changes reflect in FINAL_PRODUCTION_CONFIG.json file on disk
```

## THEN MOVE TO 04_PNL_JOURNAL_MONGODB.md.
"
Observation: Create successful: /app/frontend_fixes/03_ENABLE_CONFIG_CONTROLS.md