# 05_MARKET_STATE_MANAGEMENT.md

## Store Design
- Use **Zustand** for performant, minimal-boilerplate state management.
- Store: `useMarketStore`.
- State: `ticks`, `candles`, `activeSignals`.

    # 05_MARKET_STATE_MANAGEMENT.md
# PHASE 2 — MARKET STATE MANAGEMENT ARCHITECTURE

# OBJECTIVE

This phase focuses ONLY on:

```text
Building the centralized realtime market state management layer
```

This phase becomes:
```text
the central nervous system of the frontend
```

IMPORTANT:
This phase DOES NOT:
- build BOS overlays
- build replay system
- build execution engine
- build PostgreSQL integration
- build ML layer

This phase ONLY builds:
- Zustand market store
- realtime market state architecture
- event-driven state updates
- performant state selectors
- candle/tick/signal state management

---

# PRIMARY GOAL

At the end of this phase:

✅ Frontend has centralized realtime market state  
✅ WebSocket events dispatch safely into store  
✅ Candles update efficiently  
✅ Tick updates remain performant  
✅ Signals stored consistently  
✅ No excessive rerenders  
✅ No giant React state trees  
✅ Store architecture scalable for future phases  
✅ Chart engine consumes store efficiently  
✅ Realtime UI remains stable under heavy updates  

---

# IMPORTANT ARCHITECTURAL PRINCIPLE

# THE STORE MUST BECOME:

```text
Single Source of Truth
```

Meaning:
- charts consume store state
- UI consumes store state
- websocket layer dispatches into store
- components NEVER own realtime market state directly

---

# CRITICAL RULES

# RULE 1

DO NOT:
```text
store websocket state inside React components
```

---

# RULE 2

DO NOT:
```text
use Context API as primary market store
```

Use:
```text
Zustand
```

ONLY.

---

# RULE 3

DO NOT:
```text
store TradingView chart objects in Zustand
```

Store ONLY:
- market data
- connection state
- signal state
- chart metadata

---

# RULE 4

DO NOT:
```text
rerender entire app on every tick
```

This is EXTREMELY important.

---

# EXISTING PROJECT CONTEXT

Existing systems:
- FastAPI Market Gateway
- WebSocket frontend layer
- TradingView chart engine preparation
- React/Vite frontend
- websocket event stream

Current missing piece:
```text
centralized realtime state architecture
```

---

# REQUIRED DEPENDENCY

Install:

```bash
npm install zustand
```

OPTIONAL:
```bash
npm install immer
```

ONLY if immutability helper needed.

---

# TARGET STORE ARCHITECTURE

# FINAL FLOW

```text
WebSocket Event
       ↓
Event Parser
       ↓
Store Action
       ↓
Zustand Store
       ↓
Selective Component Updates
       ↓
TradingView Rendering
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders.

Suggested structure:

```text
frontend/src/modules/market/
│
├── store/
│   ├── useMarketStore.ts
│   ├── marketSelectors.ts
│   ├── marketActions.ts
│   ├── marketTypes.ts
│   ├── marketUtils.ts
│   ├── storeConfig.ts
│   └── marketSlices/
│       ├── tickSlice.ts
│       ├── candleSlice.ts
│       ├── signalSlice.ts
│       └── connectionSlice.ts
│
├── websocket/
│
├── charts/
│
└── utils/
```

---

# STEP 1 — STORE TYPE DEFINITIONS

# FILE

```text
marketTypes.ts
```

---

# PURPOSE

Centralized typing system for all market state.

---

# REQUIRED TYPES

Need:
- Tick
- Candle
- Signal
- Timeframe
- Symbol
- ConnectionState
- MarketState

---

# REQUIRED TICK TYPE

```typescript
{
  symbol: string
  price: number
  volume?: number
  timestamp: string
}
```

---

# REQUIRED CANDLE TYPE

```typescript
{
  symbol: string
  timeframe: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: string
}
```

---

# REQUIRED SIGNAL TYPE

```typescript
{
  signal: "BUY" | "SELL"
  symbol: string
  reason: string
  timestamp: string
}
```

---

# IMPORTANT

NO:
```text
any-type market data
```

Strict typing ONLY.

---

# STEP 2 — STORE CONFIGURATION

# FILE

```text
storeConfig.ts
```

---

# PURPOSE

Centralized store configuration.

Need:
- max tick history
- max candle history
- signal retention
- memory limits
- cache settings

---

# IMPORTANT

Realtime systems MUST:
```text
limit memory growth
```

Otherwise:
- browser freezes
- memory leaks
- degraded FPS

will happen later.

---

# REQUIRED LIMITS

Need configurable:
- tick retention count
- candle retention count
- signal retention count

---

# STEP 3 — STORE SLICES ARCHITECTURE

# IMPORTANT DECISION

Use:
```text
slice-based Zustand architecture
```

NOT:
```text
one giant store file
```

This is VERY important for scaling.

---

# REQUIRED SLICES

## tickSlice.ts
## candleSlice.ts
## signalSlice.ts
## connectionSlice.ts

---

# PURPOSE OF EACH SLICE

# tickSlice

Stores:
- latest ticks
- tick history
- latest price snapshots

---

# candleSlice

Stores:
- realtime candles
- timeframe candles
- latest candle state
- historical candle cache

---

# signalSlice

Stores:
- active signals
- signal history
- latest strategy outputs

---

# connectionSlice

Stores:
- websocket connection state
- reconnect attempts
- latency metrics later

---

# STEP 4 — MAIN STORE

# FILE

```text
useMarketStore.ts
```

---

# PURPOSE

Centralized Zustand store.

This becomes:
```text
frontend market brain
```

---

# RESPONSIBILITIES

Need:
- combine slices
- expose actions
- expose selectors
- maintain efficient subscriptions

---

# IMPORTANT

Use:
```typescript
create()
```

from Zustand.

Need:
- modular architecture
- scalable design
- minimal rerenders

---

# STEP 5 — TICK STATE MANAGEMENT

# FILE

```text
tickSlice.ts
```

---

# RESPONSIBILITIES

Need:
- latest tick updates
- symbol-based tick storage
- rolling tick history
- memory-safe tick retention

---

# REQUIRED ACTIONS

Need:
- addTick()
- clearTicks()
- trimOldTicks()

---

# IMPORTANT

DO NOT:
```text
store infinite tick history in frontend memory
```

Browser memory will explode later.

---

# REQUIRED STRATEGY

Keep:
- rolling window
- capped tick history

Example:
```text
last 1000 ticks per symbol
```

---

# STEP 6 — CANDLE STATE MANAGEMENT

# FILE

```text
candleSlice.ts
```

---

# MOST IMPORTANT SLICE

This powers:
- realtime chart rendering
- timeframe switching
- future replay engine

---

# RESPONSIBILITIES

Need:
- historical candles
- partial candles
- finalized candles
- timeframe-aware storage

---

# REQUIRED STATE STRUCTURE

Need:
```text
candles[symbol][timeframe]
```

architecture.

---

# REQUIRED ACTIONS

Need:
- setCandles()
- updateLatestCandle()
- appendCandle()
- clearCandles()

---

# IMPORTANT

DO NOT:
```text
replace full candle arrays repeatedly
```

Need:
```text
incremental updates only
```

---

# REQUIRED FLOW

# PARTIAL CANDLE

Update:
```text
latest candle only
```

---

# FINALIZED CANDLE

Append:
```text
new candle
```

---

# STEP 7 — SIGNAL STATE MANAGEMENT

# FILE

```text
signalSlice.ts
```

---

# RESPONSIBILITIES

Need:
- active signals
- signal history
- latest strategy events

---

# REQUIRED ACTIONS

Need:
- addSignal()
- clearSignals()
- removeExpiredSignals()

---

# IMPORTANT

Future overlays will depend heavily on:
```text
clean signal state architecture
```

---

# STEP 8 — CONNECTION STATE MANAGEMENT

# FILE

```text
connectionSlice.ts
```

---

# RESPONSIBILITIES

Need:
- websocket status
- reconnect state
- connection timestamps
- last heartbeat

---

# REQUIRED STATES

## CONNECTING
## CONNECTED
## DISCONNECTED
## RECONNECTING
## ERROR

---

# STEP 9 — STORE SELECTORS

# FILE

```text
marketSelectors.ts
```

---

# PURPOSE

Prevent unnecessary rerenders.

---

# IMPORTANT

Components MUST use:
```text
selectors
```

NOT:
```text
entire store subscriptions
```

---

# REQUIRED SELECTORS

Need:
- latest candle selector
- active symbol selector
- latest price selector
- signal selector
- connection selector

---

# CRITICAL PERFORMANCE RULE

Bad selectors =
```text
massive rerender storms
```

under live market conditions.

---

# STEP 10 — STORE ACTIONS

# FILE

```text
marketActions.ts
```

---

# PURPOSE

Centralized action creators.

Need:
- websocket dispatch integration
- normalized updates
- reusable actions

---

# IMPORTANT

WebSocket layer should dispatch:
```text
actions only
```

NOT mutate store directly everywhere.

---

# STEP 11 — STORE UTILITIES

# FILE

```text
marketUtils.ts
```

---

# RESPONSIBILITIES

Need:
- timestamp normalization
- candle merging
- duplicate detection
- tick trimming
- memory cleanup

---

# IMPORTANT

Duplicate events WILL happen later.

Need:
```text
deduplication utilities
```

ready now.

---

# STEP 12 — PERFORMANCE OPTIMIZATION

# CRITICAL

This phase determines:
```text
whether frontend survives live streaming
```

---

# REQUIRED OPTIMIZATIONS

## Selector-based subscriptions
## Shallow comparisons
## Incremental candle updates
## Memory caps
## Tick trimming
## Avoid giant state trees

---

# IMPORTANT

DO NOT:
```text
trigger global rerenders on every tick
```

---

# STEP 13 — MEMORY SAFETY

Need:
- capped histories
- cleanup utilities
- rolling buffers
- stale data removal

---

# CRITICAL

Realtime market systems:
```text
grow forever unless controlled
```

---

# STEP 14 — WEBSOCKET INTEGRATION

# REQUIRED FLOW

```text
WebSocket Event
      ↓
Event Parser
      ↓
Store Action
      ↓
Slice Update
      ↓
Chart/UI Update
```

---

# IMPORTANT

Store MUST remain:
```text
event-driven
```

NOT:
```text
polling-driven
```

---

# STEP 15 — CHART INTEGRATION

TradingView charts MUST consume:
```text
store selectors
```

NOT:
```text
raw websocket events
```

This is VERY important.

---

# STEP 16 — FUTURE-COMPATIBILITY REQUIREMENTS

Architecture MUST support future:

## Multi-symbol streaming
## Options chains
## Replay system
## BOS overlays
## Execution overlays
## ML streams

---

# THEREFORE

Store architecture MUST remain:
- modular
- scalable
- loosely coupled

---

# REQUIRED TESTING

Agent MUST perform:

# TEST 1
Realtime tick ingestion

# TEST 2
Realtime candle updates

# TEST 3
Signal updates

# TEST 4
Selector rerender tests

# TEST 5
Memory growth tests

# TEST 6
High-frequency update tests

# TEST 7
Multi-symbol preparation tests

# TEST 8
Store cleanup tests

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- store architecture
- slice flow
- selector strategy
- websocket dispatch flow

---

# B. FILE-BY-FILE IMPLEMENTATION

For EVERY file:
- exact path
- purpose
- integration details

---

# C. FULL PRODUCTION CODE

Need:
- actual Zustand implementation
- scalable architecture
- no pseudo code

---

# D. PERFORMANCE OBSERVATIONS

Need:
- rerender analysis
- memory observations
- selector efficiency
- tick throughput observations

---

# E. TEST RESULTS

Need proof of:
- realtime updates
- candle state updates
- memory safety
- selector optimization
- stable store architecture

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ Zustand store functional  
✅ Tick state updates correctly  
✅ Candle state updates correctly  
✅ Signal state updates correctly  
✅ Connection state updates correctly  
✅ Selectors prevent rerender storms  
✅ Memory usage remains controlled  
✅ No giant global rerenders  
✅ Charts consume store safely  
✅ WebSocket events dispatch correctly  
✅ Store architecture scalable for future phases  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- replay engine
- BOS overlays
- execution engine
- ML state streams
- options-chain multiplexing

Wait for architecture review before proceeding to:
```text
06_REALTIME_CANDLE_RENDERING.md
```