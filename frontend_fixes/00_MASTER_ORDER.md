
Action: file_editor create /app/frontend_fixes/00_MASTER_ORDER.md --file-text "# MASTER EXECUTION ORDER — Frontend Fixes Pipeline
## Run these 6 files in sequence. Each builds on the previous.

---

## FILES AND ORDER

```
Step 1: frontend_fixes/01_AUDIT_ALL_BUTTONS.md
  → Scans every React component
  → Tests every button, input, toggle, dropdown
  → Creates FRONTEND_AUDIT_REPORT.md
  → Time: ~30 minutes

Step 2: frontend_fixes/02_FIX_BROKEN_BUTTONS.md
  → Reads the audit report
  → Fixes every broken element (5 fix categories)
  → Re-tests until all pass
  → Time: ~1-2 hours

Step 3: frontend_fixes/03_ENABLE_CONFIG_CONTROLS.md
  → Adds capital editing, risk % slider
  → Adds strategy toggle grid with Enable/Disable All
  → Adds schedule controls (hours, days, SL method)
  → Adds risk limits panel
  → All save to backend immediately
  → Time: ~1 hour

Step 4: frontend_fixes/04_PNL_JOURNAL_MONGODB.md
  → Creates trade_journal collection in MongoDB Atlas
  → Adds CRUD routes for trades
  → Adds journal frontend with filters
  → Adds trade detail modal (click for ALL details)
  → Adds CSV export
  → Hooks into existing trade execution for auto-save
  → Time: ~1.5 hours

Step 5: frontend_fixes/05_LOST_TRADES_ANALYSIS.md
  → Adds loss pattern analysis tab
  → Groups losses by strategy, day, hour, regime
  → Saves analysis to MongoDB
  → Time: ~30 minutes

Step 6: frontend_fixes/06_FINAL_VALIDATION.md
  → Tests EVERY element end-to-end
  → 100+ test checklist items
  → Fixes any remaining issues
  → Creates FRONTEND_VALIDATION_COMPLETE.md
  → Time: ~1 hour
Step 7: frontend_fixes/07_BACKEND_FRONTEND_COMPLETENESS.md  ★ THE BIG ONE
  → Reads EVERY backend file (server.py, backtest_engine.py, live_state.py, risk_calculator.py, notification_service.py)
  → Reads ALL 35 modules/*.py + 12 sub-packages (smc, regime, risk_exec, etc.)
  → Reads dashboard/app.py, charts.py, loader.py
  → Creates mapping table: Backend Capability → API Route → Frontend Component
  → For EVERY missing frontend component → CREATES it (20 component templates provided)
  → Adds API routes to expose hidden backend data
  → Wires everything into navigation
  → Creates COMPLETENESS_REPORT.md (100% coverage required)
  → Time: ~2-3 hours
```

---

## HOW TO RUN

```bash
cd \"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\"

# Run each file sequentially
gemini -f frontend_fixes/01_AUDIT_ALL_BUTTONS.md
gemini -f frontend_fixes/02_FIX_BROKEN_BUTTONS.md
gemini -f frontend_fixes/03_ENABLE_CONFIG_CONTROLS.md
gemini -f frontend_fixes/04_PNL_JOURNAL_MONGODB.md
gemini -f frontend_fixes/05_LOST_TRADES_ANALYSIS.md
gemini -f frontend_fixes/06_FINAL_VALIDATION.md
gemini -f frontend_fixes/07_BACKEND_FRONTEND_COMPLETENESS.md

```

**Create the folder first:**
```bash
mkdir frontend_fixes
```


Then copy all 8 MD files into `frontend_fixes/`.


---

## TOTAL ESTIMATED TIME: 5-7 hours

## AFTER COMPLETION: Dashboard is production-ready for paper trading.
"
Observation: Create successful: /app/frontend_fixes/00_MASTER_ORDER.md