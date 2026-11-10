
Action: file_editor create /app/frontend_fixes/05_LOST_TRADES_ANALYSIS.md --file-text "# 05 — LOST TRADES ANALYSIS TAB
## Small tab showing losing trades with patterns and insights

---

## MISSION

Create a dedicated \"Lost Trades\" sub-tab in the journal that:
1. Shows only losing trades
2. Groups losses by pattern (strategy, time, day, regime)
3. Highlights which strategies/conditions consistently lose money
4. Saves this analysis to MongoDB for tracking over time

---

## BACKEND ROUTE

```python
@app.get(\"/api/journal/losses/analysis\")
def analyze_losses():
    \"\"\"Analyze losing trades for patterns.\"\"\"
    losses = list(db.trade_journal.find(
        {\"result\": \"LOSS\"}, 
        {\"_id\": 0}
    ).sort(\"pnl\", 1))
    
    if not losses:
        return {\"total_losses\": 0, \"analysis\": \"No losing trades\"}
    
    import pandas as pd
    df = pd.DataFrame(losses)
    
    analysis = {
        \"total_losses\": len(df),
        \"total_loss_amount\": round(df['pnl'].sum(), 2),
        \"avg_loss\": round(df['pnl'].mean(), 2),
        \"worst_loss\": round(df['pnl'].min(), 2),
        
        \"by_strategy\": [],
        \"by_day\": [],
        \"by_hour\": [],
        \"by_regime\": [],
        \"by_exit_reason\": [],
    }
    
    # By strategy
    if 'strategy_name' in df.columns:
        for strat, g in df.groupby('strategy_name'):
            analysis[\"by_strategy\"].append({
                \"strategy\": strat,
                \"count\": len(g),
                \"total_loss\": round(g['pnl'].sum(), 2),
                \"avg_loss\": round(g['pnl'].mean(), 2),
                \"worst\": round(g['pnl'].min(), 2),
            })
        analysis[\"by_strategy\"].sort(key=lambda x: x['total_loss'])
    
    # By day
    if 'day_of_week' in df.columns:
        for day, g in df.groupby('day_of_week'):
            analysis[\"by_day\"].append({
                \"day\": day, \"count\": len(g), \"total_loss\": round(g['pnl'].sum(), 2)
            })
    
    # By hour
    if 'hour_of_entry' in df.columns:
        for hour, g in df.groupby('hour_of_entry'):
            analysis[\"by_hour\"].append({
                \"hour\": f\"{int(hour):02d}:00\", \"count\": len(g), \"total_loss\": round(g['pnl'].sum(), 2)
            })
    
    # By regime
    if 'market_regime' in df.columns:
        for regime, g in df.groupby('market_regime'):
            analysis[\"by_regime\"].append({
                \"regime\": regime, \"count\": len(g), \"total_loss\": round(g['pnl'].sum(), 2)
            })
    
    # By exit reason
    if 'exit_reason' in df.columns:
        for reason, g in df.groupby('exit_reason'):
            analysis[\"by_exit_reason\"].append({
                \"reason\": reason, \"count\": len(g), \"total_loss\": round(g['pnl'].sum(), 2)
            })
    
    # Save analysis to MongoDB for tracking
    analysis[\"analyzed_at\"] = datetime.utcnow().isoformat()
    db.loss_analysis.insert_one({**analysis, \"timestamp\": datetime.utcnow()})
    
    return analysis
```

## FRONTEND

```jsx
function LostTradesTab() {
    const [analysis, setAnalysis] = useState(null);
    
    useEffect(() => {
        fetch(`${API_URL}/api/journal/losses/analysis`)
            .then(r => r.json())
            .then(setAnalysis);
    }, []);
    
    if (!analysis) return <div>Loading...</div>;
    
    return (
        <div className=\"loss-analysis\">
            <h3>Loss Pattern Analysis</h3>
            
            <div className=\"loss-summary\">
                <div>Total Losses: {analysis.total_losses}</div>
                <div>Total Lost: ₹{analysis.total_loss_amount?.toLocaleString()}</div>
                <div>Avg Loss: ₹{analysis.avg_loss?.toLocaleString()}</div>
                <div>Worst: ₹{analysis.worst_loss?.toLocaleString()}</div>
            </div>
            
            <h4>By Strategy (worst first)</h4>
            <table>
                <thead><tr><th>Strategy</th><th>Losses</th><th>Total Lost</th><th>Avg</th></tr></thead>
                <tbody>
                    {analysis.by_strategy?.map(s => (
                        <tr key={s.strategy}>
                            <td>{s.strategy}</td><td>{s.count}</td>
                            <td className=\"red\">₹{s.total_loss?.toLocaleString()}</td>
                            <td>₹{s.avg_loss?.toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            
            {/* Same tables for by_day, by_hour, by_regime, by_exit_reason */}
            
            <button onClick={() => {
                const blob = new Blob([JSON.stringify(analysis, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'loss_analysis.json'; a.click();
            }}>
                Save Analysis
            </button>
        </div>
    );
}
```

## THEN MOVE TO 06_FINAL_VALIDATION.md.
"
Observation: Create successful: /app/frontend_fixes/05_LOST_TRADES_ANALYSIS.md