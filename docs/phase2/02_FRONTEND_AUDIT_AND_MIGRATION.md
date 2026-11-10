# 02_FRONTEND_AUDIT_AND_MIGRATION.md

## Migration Path
- Audit existing UI components in `UI/` and `dashboard/`.
- Replace Streamlit components with React components.
- Maintain data integrity by consuming the same WebSocket JSON schemas defined in Phase 1.


# 02_FRONTEND_AUDIT_AND_MIGRATION.md
# PHASE 2 — FRONTEND AUDIT & MIGRATION STRATEGY

# OBJECTIVE

This phase focuses ONLY on:

```text
Frontend Audit + Controlled Migration Planning
```

IMPORTANT:
This phase DOES NOT:
- build TradingView charts yet
- build websocket frontend layer yet
- build Zustand store yet
- build overlays yet
- rewrite frontend yet

This phase ONLY:
- audits the current frontend
- identifies reusable components
- identifies weak architecture
- defines migration boundaries
- prepares safe integration strategy

---

# PRIMARY GOAL

Prevent:
- frontend rewrite chaos
- duplicate UI systems
- websocket conflicts
- broken routing
- component duplication
- unmaintainable architecture
- unstable migrations

At the end of this phase:

✅ Existing frontend architecture understood  
✅ Migration strategy finalized  
✅ Reusable components identified  
✅ Deprecated components identified  
✅ Streamlit coexistence plan defined  
✅ React integration boundaries finalized  
✅ Folder structure stabilized  
✅ Routing strategy finalized  
✅ Realtime rendering entry points identified  
✅ Safe incremental migration path created  

---

# EXISTING PROJECT CONTEXT

Current frontend systems:

## 1. Streamlit Dashboard
Located in:
```text
dashboard/
```

Purpose:
- analytics
- reports
- static visualization
- debugging

Current limitations:
- refresh-based rendering
- poor realtime websocket support
- limited charting
- scaling issues

---

## 2. React Frontend
Located in:
```text
AlgoTradingTelegramBotAndFrontend/
```

Purpose:
- Telegram/web UI
- existing frontend structure
- existing routing/layout

This React frontend will become:
```text
Realtime Trading Terminal
```

---

# CRITICAL MIGRATION PRINCIPLE

# DO NOT REWRITE EVERYTHING

Instead:

```text
Incrementally evolve architecture
```

This is EXTREMELY important.

---

# TARGET FINAL STATE

# STREAMLIT

Retained ONLY for:
- analytics
- debugging
- reports
- backtesting inspection
- admin utilities

---

# REACT FRONTEND

Becomes:
- realtime trading terminal
- live chart engine
- websocket rendering system
- TradingView visualization layer

---

# REQUIRED AUDIT PROCESS

# STEP 1 — COMPLETE FRONTEND STRUCTURE AUDIT

Agent MUST analyze:

```text
AlgoTradingTelegramBotAndFrontend/
dashboard/
UI/
```

Need:
- full folder tree
- routing structure
- active modules
- deprecated modules
- reusable components
- shared utilities

---

# OUTPUT REQUIRED

Agent MUST produce:

```text
FRONTEND_ARCHITECTURE_REPORT.md
```

containing:

## Existing folder tree
## Active modules
## Dead/unused modules
## Shared utilities
## Existing chart components
## Existing websocket logic
## Existing API integrations
## Existing state management
## Existing styles/themes
## Existing layouts

---

# STEP 2 — COMPONENT CLASSIFICATION

Agent MUST classify ALL frontend components into:

---

# CATEGORY A — KEEP AS-IS

Reusable without changes.

Examples:
- navigation
- authentication
- layouts
- static panels
- utility components

---

# CATEGORY B — MODIFY

Reusable with upgrades.

Examples:
- dashboard containers
- charts
- market panels
- status widgets

---

# CATEGORY C — REPLACE

Should be removed/rebuilt.

Examples:
- Streamlit realtime charts
- refresh-driven components
- polling-based rendering

---

# CATEGORY D — DEPRECATED

Unused or harmful architecture.

Examples:
- duplicate UI modules
- stale chart wrappers
- experimental dead code

---

# OUTPUT REQUIRED

Need:
```text
COMPONENT_MIGRATION_MATRIX.md
```

with:

| Component | Status | Action | Notes |
|---|---|---|---|
| ExampleChart | Replace | TradingView | Not scalable |

---

# STEP 3 — ROUTING AUDIT

Agent MUST inspect:

## Existing React routing
Need:
- page structure
- navigation flow
- route conflicts
- lazy loading support

---

# TARGET ROUTING DESIGN

Need future routes like:

```text
/dashboard
/market
/chart
/backtest
/signals
/settings
```

---

# IMPORTANT

Realtime market routes MUST remain:
- isolated
- modular
- websocket-safe

---

# OUTPUT REQUIRED

Need:
```text
ROUTING_MIGRATION_PLAN.md
```

including:
- existing routes
- new routes
- deprecated routes
- route ownership

---

# STEP 4 — STYLING SYSTEM AUDIT

Agent MUST inspect:

- CSS architecture
- theme handling
- Tailwind presence
- component styling consistency
- dark mode support

---

# IMPORTANT DECISION

Need determination:

## OPTION A
Adopt Tailwind incrementally

OR

## OPTION B
Retain current styling system temporarily

Agent MUST recommend safest path.

---

# OUTPUT REQUIRED

Need:
```text
STYLING_ARCHITECTURE_REPORT.md
```

---

# STEP 5 — WEBSOCKET ENTRY POINT AUDIT

Agent MUST identify:

- existing websocket usage
- API integrations
- polling logic
- realtime rendering entry points

---

# IMPORTANT

Need to identify:
```text
WHERE realtime market layer should attach
```

WITHOUT:
- breaking frontend
- duplicating state
- causing rerender storms

---

# OUTPUT REQUIRED

Need:
```text
WEBSOCKET_INTEGRATION_PLAN.md
```

---

# STEP 6 — STREAMLIT COEXISTENCE STRATEGY

IMPORTANT:
DO NOT immediately remove Streamlit.

Need coexistence plan.

---

# STREAMLIT RESPONSIBILITIES

Remain:
- analytics
- logs
- debugging
- admin reports

---

# REACT RESPONSIBILITIES

Become:
- realtime charting
- websocket rendering
- market visualization
- execution visualization later

---

# OUTPUT REQUIRED

Need:
```text
STREAMLIT_MIGRATION_BOUNDARY.md
```

including:
- what stays in Streamlit
- what moves to React
- what gets deprecated later

---

# STEP 7 — REALTIME ENTRY-POINT DESIGN

Agent MUST identify:
```text
best frontend integration point
```

for:
- websocket layer
- market store
- chart rendering
- realtime updates

---

# IMPORTANT

Need:
```text
minimal invasive integration
```

NOT:
```text
frontend rewrite
```

---

# TARGET INTEGRATION FLOW

```text
FastAPI WebSocket
        ↓
WebSocket Client
        ↓
Market Store
        ↓
TradingView Components
```

---

# STEP 8 — FOLDER RESTRUCTURING PLAN

IMPORTANT:
DO NOT create unnecessary folders.

Agent MUST:
- reuse existing structure
- integrate incrementally
- avoid frontend chaos

---

# TARGET MODULE STRUCTURE

Suggested ONLY if needed:

```text
frontend/src/modules/market/
```

Containing:
```text
charts/
websocket/
store/
components/
hooks/
services/
utils/
```

ONLY create missing folders.

---

# STEP 9 — DEPENDENCY AUDIT

Agent MUST inspect:
- package.json
- existing frontend dependencies
- duplicate packages
- websocket libraries
- chart libraries

---

# REQUIRED DEPENDENCIES LATER

Need preparation for:

```bash
npm install lightweight-charts zustand
```

Possibly:
```bash
npm install tailwindcss
```

BUT:
DO NOT install blindly yet.

Need dependency compatibility validation first.

---

# STEP 10 — PERFORMANCE RISK AUDIT

Agent MUST identify risks like:

- rerender-heavy components
- giant React state trees
- polling-based rendering
- blocking rendering
- memory-heavy charts
- stale subscriptions

---

# OUTPUT REQUIRED

Need:
```text
PERFORMANCE_RISK_REPORT.md
```

---

# CRITICAL MIGRATION RULES

# RULE 1

DO NOT:
```text
mix Streamlit realtime rendering with React realtime rendering
```

---

# RULE 2

DO NOT:
```text
rewrite the entire frontend
```

---

# RULE 3

DO NOT:
```text
duplicate websocket state
```

---

# RULE 4

DO NOT:
```text
keep polling-based market updates
```

Realtime websocket architecture only.

---

# RULE 5

DO NOT:
```text
start TradingView implementation yet
```

This phase is audit/planning ONLY.

---

# REQUIRED FINAL DELIVERABLES

Agent MUST produce:

# 1. FRONTEND_ARCHITECTURE_REPORT.md

# 2. COMPONENT_MIGRATION_MATRIX.md

# 3. ROUTING_MIGRATION_PLAN.md

# 4. STYLING_ARCHITECTURE_REPORT.md

# 5. WEBSOCKET_INTEGRATION_PLAN.md

# 6. STREAMLIT_MIGRATION_BOUNDARY.md

# 7. PERFORMANCE_RISK_REPORT.md

---

# REQUIRED CODE OUTPUTS

ONLY minimal safe code modifications allowed.

Possible:
- folder cleanup
- route placeholders
- module preparation

BUT:
NO major implementation yet.

---

# REQUIRED VALIDATIONS

Agent MUST verify:

✅ Existing frontend still runs  
✅ Existing routes still work  
✅ Existing backend integration intact  
✅ No broken imports  
✅ No duplicate websocket layers  
✅ Streamlit still functional  
✅ React frontend still functional  
✅ No architecture regressions introduced  

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ Frontend fully audited  
✅ Migration strategy finalized  
✅ Reusable modules identified  
✅ Deprecated modules identified  
✅ Realtime integration entry points identified  
✅ Streamlit coexistence plan finalized  
✅ Routing strategy finalized  
✅ Styling strategy finalized  
✅ Performance risks identified  
✅ Safe Phase-3 implementation path prepared  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT:
- implement TradingView charts yet
- implement websocket frontend yet
- implement Zustand yet
- implement realtime candles yet

Wait for architecture review before moving to:
```text
03_TRADINGVIEW_CHART_ENGINE.md
```