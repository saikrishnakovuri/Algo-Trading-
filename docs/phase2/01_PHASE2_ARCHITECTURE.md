# 01_PHASE2_ARCHITECTURE.md

## Overview
Phase 2 focuses on moving the visualization layer from a refresh-based Streamlit UI to a high-performance, real-time frontend powered by TradingView Lightweight Charts, connected via the FastAPI WebSocket Gateway.

## Architecture
- **Frontend**: React/TypeScript with Vite.
- **Charts**: TradingView Lightweight Charts.
- **Communication**: WebSocket connection to `ws://localhost:8001/ws/live`.
- **State**: Centralized store (Zustand) for real-time market data.



# 01_PHASE2_ARCHITECTURE.md
# PHASE 2 — REALTIME FRONTEND ARCHITECTURE
## MASTER BLUEPRINT (MOST IMPORTANT FILE)

# OBJECTIVE

Phase-2 transforms the project from:

```text
Analytics Dashboard
```

into:

```text
Realtime Trading Terminal
```

This phase introduces:

- TradingView-style realtime charting
- WebSocket-driven frontend rendering
- centralized realtime market state
- scalable frontend architecture
- production-grade realtime UI infrastructure

IMPORTANT:
This phase DOES NOT:
- replace orchestrator
- replace strategy engines
- rewrite backend architecture
- introduce ML
- introduce replay
- introduce PostgreSQL yet

This phase ONLY builds:
```text
Realtime frontend visualization infrastructure
```

---

# PRIMARY GOALS

At the end of Phase-2:

✅ Live candles render in realtime  
✅ Frontend updates without refreshes  
✅ TradingView Lightweight Charts integrated  
✅ WebSocket communication stable  
✅ Symbol switching functional  
✅ Timeframe switching functional  
✅ React architecture scalable  
✅ Realtime market store centralized  
✅ Frontend ready for BOS/CHOCH overlays later  
✅ Frontend ready for replay engine later  

---

# EXISTING PROJECT CONTEXT

Current backend:
- orchestrator.py
- FastAPI Market Gateway
- websocket broadcaster
- event stream architecture
- BOS/CHOCH/FVG logic
- paper trading
- Angel One integration

Current frontend:
- React frontend exists
- Streamlit analytics dashboard exists
- realtime rendering NOT yet production-grade

IMPORTANT:
DO NOT rewrite the frontend entirely.

Integrate incrementally.

---

# HIGH-LEVEL ARCHITECTURE

# TARGET FRONTEND ARCHITECTURE

```text
FastAPI Gateway
       ↓
WebSocket Stream
       ↓
WebSocket Client Layer
       ↓
Realtime Event Parser
       ↓
Centralized Market Store (Zustand)
       ↓
TradingView Chart Engine
       ↓
Realtime UI Components
```

---

# FRONTEND TECHNOLOGY STACK

# REQUIRED STACK

Frontend:
- React
- TypeScript
- Vite

Realtime:
- Native WebSockets

Charts:
- TradingView Lightweight Charts

State:
- Zustand

Styling:
- TailwindCSS

Utilities:
- React Query (optional later)
- Framer Motion (optional later)

---

# IMPORTANT ARCHITECTURAL DECISION

# REACT BECOMES:

```text
Realtime Trading Terminal
```

# STREAMLIT REMAINS:

```text
Analytics + Reports + Debugging
```

DO NOT attempt:
- realtime TradingView rendering in Streamlit
- websocket-heavy rendering in Streamlit

That architecture will fail under scaling.

---

# CORE FRONTEND MODULES

Create modular frontend architecture.

IMPORTANT:
Reuse existing folders whenever possible.

ONLY create missing modules.

---

# TARGET MODULE STRUCTURE

```text
frontend/src/
│
├── app/
│
├── modules/
│   ├── market/
│   │   ├── charts/
│   │   ├── websocket/
│   │   ├── store/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── components/
│   │   ├── overlays/
│   │   └── utils/
│
├── shared/
│
├── layouts/
│
├── pages/
│
└── styles/
```

DO NOT create unnecessary folders if equivalents already exist.

---

# CORE SYSTEM DESIGN

# 1. WEBSOCKET COMMUNICATION LAYER

## Purpose

Maintain persistent realtime connection with backend.

---

# DATA FLOW

```text
FastAPI WebSocket
        ↓
Frontend WebSocket Client
        ↓
Event Parser
        ↓
Market Store
        ↓
Charts/UI
```

---

# RESPONSIBILITIES

WebSocket layer MUST:
- auto reconnect
- maintain heartbeat
- detect stale connections
- handle malformed packets
- support multiple event types
- reconnect safely
- prevent duplicate subscriptions

---

# SUPPORTED EVENTS

## Tick Event

```json
{
  "type": "tick",
  "symbol": "NIFTY",
  "price": 24500,
  "timestamp": "2026-05-11T09:15:00"
}
```

---

## Candle Event

```json
{
  "type": "candle",
  "symbol": "NIFTY",
  "timeframe": "1m",
  "open": 24500,
  "high": 24520,
  "low": 24490,
  "close": 24510,
  "volume": 1200,
  "timestamp": "2026-05-11T09:15:00"
}
```

---

## Signal Event

```json
{
  "type": "signal",
  "signal": "BUY",
  "symbol": "NIFTY",
  "reason": "BOS + FVG",
  "timestamp": "2026-05-11T09:15:00"
}
```

---

# 2. MARKET STATE MANAGEMENT

# CRITICAL ARCHITECTURE DECISION

Use:
```text
Zustand
```

DO NOT:
- store websocket data directly in component state
- use excessive prop drilling
- use Context-only architecture

---

# PURPOSE OF MARKET STORE

Centralized source of truth for:

- live ticks
- live candles
- active symbol
- active timeframe
- websocket connection status
- signal events
- chart metadata

---

# STORE RESPONSIBILITIES

The market store MUST:
- process incoming websocket events
- update candles incrementally
- avoid unnecessary rerenders
- expose selectors/hooks
- maintain latest market snapshot

---

# TARGET STORE STRUCTURE

```text
marketStore
│
├── connection
├── symbols
├── ticks
├── candles
├── signals
├── chartState
└── uiState
```

---

# IMPORTANT PERFORMANCE RULE

DO NOT:
```text
rerender entire chart on every tick
```

Only:
- update latest candle
- update latest tick
- append finalized candles

This is EXTREMELY important.

---

# 3. TRADINGVIEW CHART ENGINE

# PURPOSE

Replace:
```text
static refresh charts
```

with:
```text
professional realtime market visualization
```

---

# REQUIRED CHART LIBRARY

Use:
```text
TradingView Lightweight Charts
```

DO NOT use:
- matplotlib
- generic chart wrappers
- Streamlit charts
- heavy charting libraries

---

# CHART RESPONSIBILITIES

Chart engine MUST support:

## Realtime Candle Updates
## Historical Candle Loading
## Smooth Rendering
## Crosshair
## Zoom
## Pan
## Timeframe Switching
## Responsive Resize
## Infinite History Later
## Overlay Support Later

---

# CHART DATA FLOW

```text
Market Store
      ↓
Chart Adapter
      ↓
TradingView Series
      ↓
Canvas Rendering
```

---

# IMPORTANT IMPLEMENTATION RULE

The chart MUST:
```text
incrementally update latest candle
```

NOT:
```text
rerender full candle array every tick
```

This determines:
- FPS
- latency
- memory efficiency
- scalability

---

# 4. COMPONENT HIERARCHY

# TARGET COMPONENT TREE

```text
App
│
├── TradingLayout
│
├── MarketDashboard
│   │
│   ├── TopBar
│   ├── SymbolSelector
│   ├── TimeframeSelector
│   ├── ConnectionStatus
│   │
│   ├── TradingChart
│   │   ├── CandleSeries
│   │   ├── VolumeSeries
│   │   └── OverlayLayer
│   │
│   ├── MarketSidebar
│   │
│   ├── SignalPanel
│   │
│   └── EventLog
```

---

# RESPONSIBILITIES

# TopBar
- symbol
- timeframe
- websocket status
- market status

# TradingChart
- realtime rendering
- chart lifecycle
- chart synchronization

# SignalPanel
- realtime strategy signals

# EventLog
- websocket events
- reconnects
- warnings
- errors

---

# 5. EVENT LIFECYCLE

# COMPLETE EVENT FLOW

```text
Broker Tick
      ↓
Broker Adapter
      ↓
websocket_manager.py
      ↓
orchestrator.py
      ↓
event_stream.py
      ↓
FastAPI WebSocket
      ↓
Frontend WebSocket Client
      ↓
Event Parser
      ↓
Zustand Store
      ↓
TradingView Chart
```

This lifecycle MUST remain:
- asynchronous
- non-blocking
- event-driven

---

# 6. REALTIME CANDLE FLOW

# CANDLE UPDATE FLOW

```text
New Candle Event
      ↓
WebSocket Received
      ↓
Validate Event
      ↓
Update Market Store
      ↓
Update Latest Candle
      ↓
TradingView update()
```

DO NOT:
```text
replace entire candle dataset
```

This is a CRITICAL architecture rule.

---

# 7. TIMEFRAME SWITCHING ARCHITECTURE

# REQUIRED TIMEFRAMES

```text
1m
5m
15m
1h
4h
1D
```

---

# SWITCHING FLOW

```text
User Changes Timeframe
        ↓
Frontend Updates State
        ↓
Request Historical Candles
        ↓
Reset Chart Series
        ↓
Resume Live Streaming
```

---

# IMPORTANT

Timeframe switching MUST:
- preserve websocket connection
- avoid duplicate subscriptions
- avoid stale chart data

---

# 8. SYMBOL SWITCHING ARCHITECTURE

# REQUIRED SUPPORT

Support:
- NIFTY
- BANKNIFTY
- FINNIFTY
- Equities later
- Options later

---

# SYMBOL FLOW

```text
User Changes Symbol
        ↓
Store Updates
        ↓
Historical Data Reload
        ↓
Chart Reset
        ↓
Live Stream Resume
```

---

# 9. ERROR HANDLING ARCHITECTURE

# REQUIRED HANDLING

Handle:
- websocket disconnects
- malformed packets
- stale connections
- backend downtime
- frontend reloads
- duplicate events

---

# REQUIRED UI STATES

Need visible:
- reconnecting
- disconnected
- connected
- stale data
- loading history

---

# 10. PERFORMANCE ARCHITECTURE

# CRITICAL

Realtime frontend performance determines:
- UX quality
- replay feasibility
- overlay scalability
- multi-symbol scalability

---

# PERFORMANCE RULES

# RULE 1
DO NOT rerender chart unnecessarily.

# RULE 2
Use memoization aggressively.

# RULE 3
Throttle websocket UI updates if required.

# RULE 4
Update only changed candles.

# RULE 5
Avoid huge React state trees.

---

# TARGET PERFORMANCE

Need:
- smooth realtime rendering
- low CPU usage
- stable memory usage
- high FPS rendering
- scalable websocket throughput

---

# 11. FUTURE-COMPATIBILITY REQUIREMENTS

This architecture MUST support future phases.

---

# FUTURE PHASES

Later phases include:

## Phase-3
Tick database

## Phase-4
Custom candle engine

## Phase-5
BOS/CHOCH overlays

## Phase-6
Replay system

## Phase-7
Execution visualization

## Phase-8
ML overlays

---

# THEREFORE

Frontend architecture MUST remain:
- modular
- event-driven
- scalable
- loosely coupled

---

# 12. IMPLEMENTATION ORDER

Agent MUST implement in THIS order ONLY.

# STEP-1
Frontend audit

# STEP-2
WebSocket frontend layer

# STEP-3
Zustand market store

# STEP-4
TradingView chart integration

# STEP-5
Realtime candle rendering

# STEP-6
Timeframe switching

# STEP-7
Symbol switching

# STEP-8
Performance optimization

# STEP-9
Reconnect/error handling

# STEP-10
Validation testing

---

# 13. OUTPUT REQUIREMENTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- frontend data flow
- websocket lifecycle
- state lifecycle
- chart lifecycle

---

# B. FILE-BY-FILE IMPLEMENTATION

For EVERY file:
- exact path
- purpose
- integration details

---

# C. FULL CODE

Need:
- production-quality code
- no pseudo code
- scalable implementation

---

# D. PERFORMANCE OBSERVATIONS

Need:
- FPS observations
- rerender analysis
- websocket throughput
- memory observations

---

# E. TEST RESULTS

Need proof of:

## Live websocket rendering
## Realtime candle updates
## Timeframe switching
## Symbol switching
## Reconnect handling
## Multi-event processing

---

# 14. PHASE-2 SUCCESS CRITERIA

PHASE-2 is COMPLETE ONLY IF:

✅ TradingView charts render successfully  
✅ Live candles update in realtime  
✅ WebSocket integration stable  
✅ No refresh-based rendering  
✅ Zustand store functional  
✅ Timeframe switching works  
✅ Symbol switching works  
✅ Reconnect handling works  
✅ Performance remains smooth  
✅ Existing backend remains functional  
✅ Streamlit can coexist temporarily  
✅ Architecture ready for overlays later  

---

# 15. IMPORTANT FINAL INSTRUCTION

After Phase-2 implementation:

STOP.

DO NOT continue to:
- BOS overlays
- replay system
- PostgreSQL migration
- custom candle engine
- ML visualization

Wait for architecture review before proceeding.