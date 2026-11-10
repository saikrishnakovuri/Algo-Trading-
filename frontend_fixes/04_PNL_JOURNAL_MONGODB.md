
Action: file_editor create /app/frontend_fixes/04_PNL_JOURNAL_MONGODB.md --file-text "# 04 — P&L JOURNAL WITH MONGODB ATLAS
## Every trade saved to MongoDB, viewable & exportable from frontend

---

## MISSION

Build a P&L Trade Journal that:
1. **Saves EVERY trade** (live + backtest) to MongoDB Atlas
2. **Shows full trade list** in a frontend table — P&L, quantity, strategy, timestamps
3. **Click any trade for FULL details** — entry price, exit price, target, SL, strategy for SL/TP, which strategy, market regime, confidence, duration, everything
4. **Export to CSV/Excel** anytime with one click
5. **Filter by date, strategy, result, P&L range**

**Data store:** MongoDB Atlas (already connected per your setup)

---

## STEP 1: FIND EXISTING MONGODB CONNECTION

Search the codebase for the existing MongoDB connection:

```bash
grep -rn \"mongo\|MONGO\|pymongo\|motor\|MongoClient\" AlgoTradingTelegramBotAndFrontend/backend/ --include=\"*.py\"
grep -rn \"MONGO\" AlgoTradingTelegramBotAndFrontend/backend/.env
grep -rn \"mongo\|MONGO\" .env
```

Use the EXISTING connection. Do NOT create a new one.

---

## STEP 2: CREATE THE TRADE JOURNAL COLLECTION

**Collection name:** `trade_journal`

**Document schema:**

```python
trade_document = {
    # Core identifiers
    \"trade_id\": \"TJ-20260510-001\",        # Auto-generated unique ID
    \"timestamp\": datetime.utcnow(),         # When the document was created
    
    # Trade basics (VISIBLE IN TABLE)
    \"symbol\": \"NIFTY\",
    \"direction\": \"CE\",                      # CE (bullish) / PE (bearish)
    \"quantity\": 50,
    \"entry_price\": 23450.50,
    \"exit_price\": 23520.75,
    \"pnl\": 3512.50,                         # Net P&L in ₹
    \"pnl_pct\": 0.70,                        # P&L as % of capital
    \"result\": \"WIN\",                         # WIN / LOSS / BREAKEVEN / OPEN
    
    # Timing
    \"entry_time\": \"2026-05-10T10:15:00\",
    \"exit_time\": \"2026-05-10T11:42:00\",
    \"holding_period_minutes\": 87,
    
    # Strategy details (VISIBLE ON CLICK → Details)
    \"strategy_name\": \"Breakout-Retest-Continuation\",
    \"strategy_category\": \"price_action_pattern\",
    \"signal_confidence\": 0.87,
    \"signal_type\": \"BUY\",
    
    # Stop loss & target details
    \"stop_loss\": 23380.00,
    \"take_profit\": 23600.00,
    \"sl_method\": \"ATR_TRAILING\",
    \"sl_atr_multiplier\": 2.0,
    \"initial_risk\": 70.50,                  # Entry - SL per unit
    \"risk_reward_target\": 3.0,
    \"risk_reward_achieved\": 1.85,
    
    # Exit details
    \"exit_reason\": \"TRAIL_HIT\",             # SL_HIT / TP_HIT / TRAIL_HIT / MANUAL / EOD / TIME
    \"trailing_sl_at_exit\": 23500.00,
    
    # Market context
    \"market_regime\": \"TRENDING_UP\",
    \"atr_at_entry\": 35.25,
    \"vix_at_entry\": 14.2,
    \"day_of_week\": \"Thursday\",
    \"hour_of_entry\": 10,
    
    # Capital tracking
    \"capital_before\": 514000,
    \"capital_after\": 517512.50,
    \"cumulative_pnl\": 17512.50,
    
    # Source
    \"source\": \"live\",                       # \"live\" / \"paper\" / \"backtest\"
    \"mode\": \"PAPER\",                        # PAPER / LIVE
    
    # Options specific (if applicable)
    \"option_type\": \"CE\",
    \"strike_price\": 23400,
    \"expiry\": \"2026-05-15\",
    \"premium_paid\": 120.50,
    \"premium_received\": 145.75,
}
```

---

## STEP 3: BACKEND — TRADE JOURNAL ROUTES

**Append to `AlgoTradingTelegramBotAndFrontend/backend/server.py`:**

```python
from datetime import datetime, timedelta
from bson import ObjectId
import csv
import io

# Use existing MongoDB connection
# db = ... (find your existing db variable)

# Helper to make ObjectId JSON-safe
def serialize_trade(trade):
    trade[\"_id\"] = str(trade[\"_id\"])
    return trade

# --- TRADE JOURNAL ROUTES ---

@app.get(\"/api/journal/trades\")
async def get_journal_trades(
    page: int = 1,
    limit: int = 50,
    strategy: str = None,
    result: str = None,
    start_date: str = None,
    end_date: str = None,
    min_pnl: float = None,
    max_pnl: float = None,
    source: str = None,
    sort_by: str = \"entry_time\",
    sort_order: str = \"desc\"
):
    \"\"\"Get paginated, filtered trade journal entries.\"\"\"
    query = {}
    
    if strategy:
        query[\"strategy_name\"] = strategy
    if result:
        query[\"result\"] = result
    if source:
        query[\"source\"] = source
    if start_date:
        query[\"entry_time\"] = {\"$gte\": start_date}
    if end_date:
        query.setdefault(\"entry_time\", {})[\"$lte\"] = end_date
    if min_pnl is not None:
        query[\"pnl\"] = {\"$gte\": min_pnl}
    if max_pnl is not None:
        query.setdefault(\"pnl\", {})[\"$lte\"] = max_pnl
    
    sort_dir = -1 if sort_order == \"desc\" else 1
    
    total = db.trade_journal.count_documents(query)
    trades = list(
        db.trade_journal.find(query, {\"_id\": 0})
        .sort(sort_by, sort_dir)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    
    # Summary stats
    all_trades_pnl = list(db.trade_journal.find(query, {\"pnl\": 1, \"result\": 1, \"_id\": 0}))
    total_pnl = sum(t.get(\"pnl\", 0) for t in all_trades_pnl)
    wins = sum(1 for t in all_trades_pnl if t.get(\"result\") == \"WIN\")
    
    return {
        \"trades\": trades,
        \"total\": total,
        \"page\": page,
        \"pages\": (total + limit - 1) // limit,
        \"summary\": {
            \"total_trades\": total,
            \"total_pnl\": round(total_pnl, 2),
            \"wins\": wins,
            \"losses\": total - wins,
            \"win_rate\": round(wins / max(total, 1) * 100, 1),
        }
    }


@app.get(\"/api/journal/trade/{trade_id}\")
def get_trade_detail(trade_id: str):
    \"\"\"Get FULL details of a single trade.\"\"\"
    trade = db.trade_journal.find_one({\"trade_id\": trade_id}, {\"_id\": 0})
    if not trade:
        return {\"error\": \"Trade not found\"}
    return trade


@app.post(\"/api/journal/trade\")
async def save_trade(request: Request):
    \"\"\"Save a new trade to the journal (called by bot/backtest).\"\"\"
    trade = await request.json()
    
    # Auto-generate trade_id if not provided
    if \"trade_id\" not in trade:
        count = db.trade_journal.count_documents({}) + 1
        trade[\"trade_id\"] = f\"TJ-{datetime.now().strftime('%Y%m%d')}-{count:04d}\"
    
    trade[\"timestamp\"] = datetime.utcnow().isoformat()
    
    db.trade_journal.insert_one(trade)
    # Remove _id for response
    trade.pop(\"_id\", None)
    
    return {\"status\": \"saved\", \"trade_id\": trade[\"trade_id\"]}


@app.post(\"/api/journal/import\")
async def import_trades_from_csv(request: Request):
    \"\"\"Import trades from a CSV file (for backtest results).\"\"\"
    data = await request.json()
    csv_path = data.get(\"csv_path\")
    source = data.get(\"source\", \"backtest\")
    
    if not csv_path or not os.path.exists(csv_path):
        return {\"error\": \"CSV file not found\"}
    
    import pandas as pd
    df = pd.read_csv(csv_path)
    
    count = 0
    for _, row in df.iterrows():
        trade = row.to_dict()
        trade[\"source\"] = source
        trade[\"trade_id\"] = f\"TJ-{source[:2].upper()}-{count:06d}\"
        trade[\"timestamp\"] = datetime.utcnow().isoformat()
        
        # Clean NaN values
        trade = {k: v for k, v in trade.items() if pd.notna(v)}
        
        db.trade_journal.insert_one(trade)
        count += 1
    
    return {\"status\": \"imported\", \"count\": count}


@app.get(\"/api/journal/export\")
async def export_journal(
    format: str = \"csv\",
    start_date: str = None,
    end_date: str = None,
    strategy: str = None,
):
    \"\"\"Export trade journal as CSV.\"\"\"
    query = {}
    if start_date: query[\"entry_time\"] = {\"$gte\": start_date}
    if end_date: query.setdefault(\"entry_time\", {})[\"$lte\"] = end_date
    if strategy: query[\"strategy_name\"] = strategy
    
    trades = list(db.trade_journal.find(query, {\"_id\": 0}).sort(\"entry_time\", -1))
    
    if format == \"csv\":
        if not trades:
            return {\"error\": \"No trades to export\"}
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type=\"text/csv\",
            headers={\"Content-Disposition\": f\"attachment; filename=trade_journal_{datetime.now().strftime('%Y%m%d')}.csv\"}
        )
    
    return {\"trades\": trades, \"count\": len(trades)}


@app.get(\"/api/journal/summary\")
def get_journal_summary():
    \"\"\"Get overall journal statistics.\"\"\"
    pipeline = [
        {\"$group\": {
            \"_id\": None,
            \"total_trades\": {\"$sum\": 1},
            \"total_pnl\": {\"$sum\": \"$pnl\"},
            \"avg_pnl\": {\"$avg\": \"$pnl\"},
            \"max_pnl\": {\"$max\": \"$pnl\"},
            \"min_pnl\": {\"$min\": \"$pnl\"},
            \"wins\": {\"$sum\": {\"$cond\": [{\"$eq\": [\"$result\", \"WIN\"]}, 1, 0]}},
        }}
    ]
    result = list(db.trade_journal.aggregate(pipeline))
    
    if not result:
        return {\"total_trades\": 0, \"total_pnl\": 0}
    
    stats = result[0]
    stats.pop(\"_id\", None)
    stats[\"win_rate\"] = round(stats[\"wins\"] / max(stats[\"total_trades\"], 1) * 100, 1)
    
    # Per-strategy breakdown
    strat_pipeline = [
        {\"$group\": {
            \"_id\": \"$strategy_name\",
            \"trades\": {\"$sum\": 1},
            \"pnl\": {\"$sum\": \"$pnl\"},
            \"wins\": {\"$sum\": {\"$cond\": [{\"$eq\": [\"$result\", \"WIN\"]}, 1, 0]}},
        }},
        {\"$sort\": {\"pnl\": -1}}
    ]
    stats[\"by_strategy\"] = list(db.trade_journal.aggregate(strat_pipeline))
    
    # Per-day breakdown
    day_pipeline = [
        {\"$group\": {
            \"_id\": \"$day_of_week\",
            \"trades\": {\"$sum\": 1},
            \"pnl\": {\"$sum\": \"$pnl\"},
        }},
        {\"$sort\": {\"pnl\": -1}}
    ]
    stats[\"by_day\"] = list(db.trade_journal.aggregate(day_pipeline))
    
    return stats


@app.get(\"/api/journal/strategies\")
def get_journal_strategies():
    \"\"\"Get list of all strategies used in journal for filter dropdown.\"\"\"
    strategies = db.trade_journal.distinct(\"strategy_name\")
    return sorted([s for s in strategies if s])
```

---

## STEP 4: HOOK INTO EXISTING TRADE EXECUTION

Find where trades are executed in the existing codebase and add a journal save call.

```bash
# Find where trades are logged/executed
grep -rn \"trade_log\|execute_trade\|place_order\|order_placed\|trade_complete\|on_trade\" modules/ --include=\"*.py\" | grep -v \"__pycache__\"
```

At the point where a trade completes (entry or exit), ADD:

```python
# ADD this after a trade is completed (don't change existing logic)
try:
    import requests
    trade_data = {
        \"symbol\": symbol,
        \"direction\": direction,
        \"entry_price\": entry_price,
        \"exit_price\": exit_price,
        \"pnl\": pnl,
        \"result\": \"WIN\" if pnl > 0 else \"LOSS\",
        \"strategy_name\": strategy_name,
        \"stop_loss\": sl,
        \"take_profit\": tp,
        # ... add all available fields
        \"source\": \"live\",
    }
    requests.post(\"http://localhost:PORT/api/journal/trade\", json=trade_data, timeout=2)
except:
    pass  # Don't let journal failure break trading
```

---

## STEP 5: FRONTEND — TRADE JOURNAL COMPONENT

### Main Journal Table

```jsx
function TradeJournal() {
    const [trades, setTrades] = useState([]);
    const [filters, setFilters] = useState({});
    const [selectedTrade, setSelectedTrade] = useState(null);
    const [summary, setSummary] = useState({});
    const [page, setPage] = useState(1);
    
    // Fetch trades with filters
    const fetchTrades = async () => {
        const params = new URLSearchParams({ page, limit: 50, ...filters });
        const res = await fetch(`${API_URL}/api/journal/trades?${params}`);
        const data = await res.json();
        setTrades(data.trades);
        setSummary(data.summary);
    };
    
    // Export
    const exportCSV = () => {
        window.open(`${API_URL}/api/journal/export?format=csv`);
    };
    
    return (
        <div className=\"trade-journal\">
            {/* Summary bar */}
            <div className=\"journal-summary\">
                <div>Total Trades: {summary.total_trades}</div>
                <div>P&L: ₹{summary.total_pnl?.toLocaleString()}</div>
                <div>Win Rate: {summary.win_rate}%</div>
                <button onClick={exportCSV}>Export CSV</button>
            </div>
            
            {/* Filters */}
            <div className=\"journal-filters\">
                <select onChange={e => setFilters({...filters, strategy: e.target.value})}>
                    <option value=\"\">All Strategies</option>
                    {/* Populate from /api/journal/strategies */}
                </select>
                <select onChange={e => setFilters({...filters, result: e.target.value})}>
                    <option value=\"\">All Results</option>
                    <option value=\"WIN\">Wins Only</option>
                    <option value=\"LOSS\">Losses Only</option>
                </select>
                <input type=\"date\" onChange={e => setFilters({...filters, start_date: e.target.value})} />
                <input type=\"date\" onChange={e => setFilters({...filters, end_date: e.target.value})} />
            </div>
            
            {/* Trade table */}
            <table className=\"journal-table\">
                <thead>
                    <tr>
                        <th>Date</th><th>Symbol</th><th>Direction</th>
                        <th>Strategy</th><th>Qty</th><th>P&L</th>
                        <th>Result</th><th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {trades.map(t => (
                        <tr key={t.trade_id} className={t.pnl > 0 ? 'win-row' : 'loss-row'}>
                            <td>{t.entry_time?.slice(0,16)}</td>
                            <td>{t.symbol}</td>
                            <td>{t.direction}</td>
                            <td>{t.strategy_name}</td>
                            <td>{t.quantity}</td>
                            <td className={t.pnl > 0 ? 'green' : 'red'}>
                                ₹{t.pnl?.toLocaleString()}
                            </td>
                            <td>{t.result}</td>
                            <td>
                                <button onClick={() => setSelectedTrade(t)}>
                                    View Details
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            
            {/* Trade Detail Modal */}
            {selectedTrade && (
                <TradeDetailModal 
                    trade={selectedTrade} 
                    onClose={() => setSelectedTrade(null)} 
                />
            )}
        </div>
    );
}
```

### Trade Detail Modal (on click)

```jsx
function TradeDetailModal({ trade, onClose }) {
    return (
        <div className=\"modal-overlay\" onClick={onClose}>
            <div className=\"modal-content\" onClick={e => e.stopPropagation()}>
                <h2>Trade Details — {trade.trade_id}</h2>
                <button className=\"close-btn\" onClick={onClose}>×</button>
                
                <div className=\"detail-grid\">
                    <Section title=\"Basic Info\">
                        <Row label=\"Symbol\" value={trade.symbol} />
                        <Row label=\"Direction\" value={trade.direction} />
                        <Row label=\"Result\" value={trade.result} highlight />
                        <Row label=\"P&L\" value={`₹${trade.pnl?.toLocaleString()}`} 
                             color={trade.pnl > 0 ? 'green' : 'red'} />
                        <Row label=\"P&L %\" value={`${trade.pnl_pct}%`} />
                        <Row label=\"Quantity\" value={trade.quantity} />
                    </Section>
                    
                    <Section title=\"Prices\">
                        <Row label=\"Entry Price\" value={`₹${trade.entry_price}`} />
                        <Row label=\"Exit Price\" value={`₹${trade.exit_price}`} />
                        <Row label=\"Stop Loss\" value={`₹${trade.stop_loss}`} />
                        <Row label=\"Take Profit\" value={`₹${trade.take_profit}`} />
                        <Row label=\"Trailing SL at Exit\" value={`₹${trade.trailing_sl_at_exit}`} />
                    </Section>
                    
                    <Section title=\"Strategy\">
                        <Row label=\"Strategy\" value={trade.strategy_name} />
                        <Row label=\"Category\" value={trade.strategy_category} />
                        <Row label=\"Confidence\" value={`${(trade.signal_confidence * 100).toFixed(0)}%`} />
                        <Row label=\"SL Method\" value={trade.sl_method} />
                        <Row label=\"ATR Multiplier\" value={trade.sl_atr_multiplier} />
                        <Row label=\"RR Target\" value={`${trade.risk_reward_target}:1`} />
                        <Row label=\"RR Achieved\" value={`${trade.risk_reward_achieved}:1`} />
                    </Section>
                    
                    <Section title=\"Timing\">
                        <Row label=\"Entry Time\" value={trade.entry_time} />
                        <Row label=\"Exit Time\" value={trade.exit_time} />
                        <Row label=\"Duration\" value={`${trade.holding_period_minutes} min`} />
                        <Row label=\"Exit Reason\" value={trade.exit_reason} />
                        <Row label=\"Day\" value={trade.day_of_week} />
                    </Section>
                    
                    <Section title=\"Market Context\">
                        <Row label=\"Regime\" value={trade.market_regime} />
                        <Row label=\"ATR\" value={trade.atr_at_entry} />
                        <Row label=\"VIX\" value={trade.vix_at_entry} />
                    </Section>
                    
                    <Section title=\"Capital\">
                        <Row label=\"Capital Before\" value={`₹${trade.capital_before?.toLocaleString()}`} />
                        <Row label=\"Capital After\" value={`₹${trade.capital_after?.toLocaleString()}`} />
                        <Row label=\"Cumulative P&L\" value={`₹${trade.cumulative_pnl?.toLocaleString()}`} />
                        <Row label=\"Source\" value={trade.source} />
                        <Row label=\"Mode\" value={trade.mode} />
                    </Section>
                </div>
            </div>
        </div>
    );
}
```

---

## STEP 6: CREATE MONGODB INDEX

```python
# Add to server startup
db.trade_journal.create_index([(\"entry_time\", -1)])
db.trade_journal.create_index([(\"strategy_name\", 1)])
db.trade_journal.create_index([(\"result\", 1)])
db.trade_journal.create_index([(\"trade_id\", 1)], unique=True)
db.trade_journal.create_index([(\"source\", 1)])
```

---

## VALIDATION

```
[ ] POST /api/journal/trade → saves to MongoDB Atlas
[ ] GET /api/journal/trades → returns paginated trades
[ ] GET /api/journal/trade/{id} → returns full detail
[ ] GET /api/journal/export?format=csv → downloads CSV
[ ] GET /api/journal/summary → returns stats
[ ] Filters work (strategy, date, result, P&L range)
[ ] Trade detail modal shows ALL fields
[ ] Export button downloads complete journal
[ ] Trades from live bot auto-save to journal
```

## THEN MOVE TO 05_TRADE_DETAIL_VIEW.md.
"
Observation: Create successful: /app/frontend_fixes/04_PNL_JOURNAL_MONGODB.md