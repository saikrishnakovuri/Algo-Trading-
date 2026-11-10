# 04_WEBSOCKET_FRONTEND_LAYER.md

## Implementation
- WebSocket custom hook `useMarketStream`.
- Auto-reconnect logic.
- Dispatch updates to the global state store.


# 04_WEBSOCKET_FRONTEND_LAYER.md
# PHASE 2 — WEBSOCKET FRONTEND LAYER

# OBJECTIVE

This phase focuses ONLY on:

```text
Building the realtime frontend WebSocket communication layer
```

This phase is the:
```text
live nervous system of the frontend
```

IMPORTANT:
This phase DOES NOT:
- build TradingView overlays
- build replay engine
- build execution engine
- build ML layer
- build custom candle engine

This phase ONLY builds:
- websocket connection layer
- realtime event ingestion
- reconnect handling
- connection lifecycle management
- event normalization
- state dispatch pipeline

---

# PRIMARY GOAL

At the end of this phase:

✅ Frontend maintains stable websocket connection  
✅ Auto reconnect works  
✅ Connection lifecycle managed correctly  
✅ Realtime events flow into frontend safely  
✅ Events dispatch into centralized market store  
✅ No duplicate websocket connections  
✅ No memory leaks  
✅ No reconnect storms  
✅ Websocket architecture scalable for future phases  
✅ Frontend ready for realtime chart rendering  

---

# IMPORTANT ARCHITECTURAL PRINCIPLE

# THIS LAYER MUST REMAIN:

```text
UI-agnostic
```

Meaning:
- websocket layer should NOT know about charts
- websocket layer should NOT directly manipulate UI
- websocket layer should NOT tightly couple with components

Architecture MUST remain:

```text
WebSocket
      ↓
Event Parser
      ↓
Market Store
      ↓
UI Components
```

This separation is CRITICAL.

---

# EXISTING PROJECT CONTEXT

Backend already exists:
- FastAPI Market Gateway
- websocket broadcaster
- /ws/live endpoint
- event stream architecture
- orchestrator event publishing

Frontend already exists:
- React/Vite frontend
- TradingView chart engine preparation
- frontend audit completed

---

# TARGET WEBSOCKET ARCHITECTURE

# FINAL FLOW

```text
FastAPI WebSocket
        ↓
Frontend WebSocket Client
        ↓
Event Validation
        ↓
Event Normalization
        ↓
Reconnect Management
        ↓
Dispatch to Zustand Store
        ↓
Charts/UI consume state
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders.

Suggested structure:

```text
frontend/src/modules/market/
│
├── websocket/
│   ├── useMarketStream.ts
│   ├── websocketClient.ts
│   ├── websocketTypes.ts
│   ├── websocketEvents.ts
│   ├── reconnectManager.ts
│   ├── heartbeatManager.ts
│   ├── streamConfig.ts
│   └── websocketUtils.ts
│
├── store/
│
├── charts/
│
└── utils/
```

---

# STEP 1 — WEBSOCKET CLIENT CORE

# FILE

```text
websocketClient.ts
```

---

# PURPOSE

Core websocket communication engine.

This file MUST:
- create websocket connection
- manage socket lifecycle
- expose connect/disconnect methods
- expose event listeners
- remain reusable
- remain UI-independent

---

# REQUIRED FEATURES

## Connect
## Disconnect
## Reconnect
## Heartbeat
## Event Dispatch
## Error Handling
## Cleanup
## Connection Status Tracking

---

# IMPORTANT

DO NOT:
```text
open websocket connections directly inside UI components
```

Centralize websocket architecture.

---

# REQUIRED WEBSOCKET ENDPOINT

Connect to:

```text
ws://localhost:8001/ws/live
```

Later:
- configurable environments
- production URLs
- auth headers

---

# STEP 2 — WEBSOCKET TYPES

# FILE

```text
websocketTypes.ts
```

---

# PURPOSE

Centralized websocket event typing.

Need strong typing for:

## TickEvent
## CandleEvent
## SignalEvent
## SystemEvent
## ConnectionState

---

# REQUIRED TYPES

# TickEvent

```typescript
{
  type: "tick"
  symbol: string
  price: number
  timestamp: string
}
```

---

# CandleEvent

```typescript
{
  type: "candle"
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

# SignalEvent

```typescript
{
  type: "signal"
  signal: string
  symbol: string
  reason: string
  timestamp: string
}
```

---

# IMPORTANT

NO:
```text
any-type websocket events
```

Strict typing ONLY.

---

# STEP 3 — STREAM CONFIGURATION

# FILE

```text
streamConfig.ts
```

---

# PURPOSE

Centralized websocket configuration.

Need:
- websocket URL
- reconnect delay
- max reconnect attempts
- heartbeat interval
- timeout duration

---

# REQUIRED CONFIGS

## DEV URL
## PROD URL
## Retry Backoff
## Connection Timeout
## Heartbeat Interval

---

# IMPORTANT

DO NOT:
```text
hardcode websocket URLs everywhere
```

---

# STEP 4 — AUTO RECONNECT ENGINE

# FILE

```text
reconnectManager.ts
```

---

# MOST IMPORTANT PART OF THIS PHASE

Realtime systems DIE here if implemented badly.

---

# RESPONSIBILITIES

Need:
- reconnect after disconnect
- exponential backoff
- prevent reconnect storms
- connection retry limits
- stale connection detection

---

# REQUIRED RECONNECT FLOW

```text
Connection Lost
      ↓
Wait Retry Delay
      ↓
Reconnect Attempt
      ↓
Restore Event Stream
      ↓
Update Connection Status
```

---

# IMPORTANT

DO NOT:
```text
spam reconnect attempts continuously
```

Need:
```text
controlled retry strategy
```

---

# REQUIRED STRATEGY

Use:
```text
exponential backoff
```

Example:
```text
1s
2s
4s
8s
16s
```

---

# STEP 5 — HEARTBEAT MANAGEMENT

# FILE

```text
heartbeatManager.ts
```

---

# PURPOSE

Detect dead/stale websocket connections.

---

# RESPONSIBILITIES

Need:
- heartbeat tracking
- stale socket detection
- timeout handling
- reconnect triggering

---

# IMPORTANT

Without heartbeat handling:
- frozen charts
- silent stale data
- invisible disconnects

become common.

---

# REQUIRED HEARTBEAT FLOW

```text
Heartbeat Received
       ↓
Update Last Alive Timestamp
```

If timeout exceeded:
```text
Force reconnect
```

---

# STEP 6 — WEBSOCKET EVENT PARSER

# FILE

```text
websocketEvents.ts
```

---

# PURPOSE

Normalize incoming websocket events.

---

# RESPONSIBILITIES

Need:
- event validation
- malformed packet handling
- schema parsing
- safe dispatch logic

---

# REQUIRED EVENT TYPES

Handle:
- tick
- candle
- signal
- system
- error

---

# IMPORTANT

DO NOT:
```text
dispatch raw websocket packets directly to store
```

Need normalization layer.

---

# STEP 7 — GLOBAL STREAM HOOK

# FILE

```text
useMarketStream.ts
```

---

# PURPOSE

Frontend integration hook.

This becomes:
```text
entry point for realtime market stream
```

---

# RESPONSIBILITIES

Need:
- initialize websocket
- attach listeners
- dispatch to store
- cleanup on unmount
- expose connection status

---

# IMPORTANT

Hook MUST:
- avoid duplicate connections
- avoid reconnect duplication
- remain lightweight

---

# REQUIRED FLOW

```text
App Loads
      ↓
useMarketStream()
      ↓
Connect WebSocket
      ↓
Receive Events
      ↓
Dispatch to Store
      ↓
UI Updates Automatically
```

---

# STEP 8 — STORE DISPATCH INTEGRATION

IMPORTANT:
This phase integrates with Zustand architecture.

---

# REQUIRED ACTIONS

Need dispatch functions for:
- addTick()
- updateCandle()
- addSignal()
- setConnectionState()

---

# IMPORTANT

Websocket layer MUST:
```text
dispatch actions only
```

NOT manipulate charts directly.

---

# STEP 9 — CONNECTION STATE MANAGEMENT

Need frontend-visible states:

## CONNECTING
## CONNECTED
## DISCONNECTED
## RECONNECTING
## ERROR

---

# REQUIRED UI SUPPORT

Later UI components should easily show:
- green live dot
- reconnect spinner
- disconnected warning

---

# STEP 10 — DUPLICATE CONNECTION PREVENTION

# CRITICAL

Need singleton-style websocket architecture.

Prevent:
- multiple websocket instances
- duplicated events
- duplicate dispatches
- reconnect loops

---

# IMPORTANT

ONLY ONE active market websocket connection allowed.

---

# STEP 11 — ERROR HANDLING

Need handling for:

## Malformed JSON
## Invalid Event Types
## Broken Packets
## Server Disconnects
## Heartbeat Failures
## Browser Refreshes
## Route Changes

---

# REQUIRED LOGGING

Need structured frontend logs for:

## Connection Open
## Connection Closed
## Reconnect Attempt
## Event Received
## Event Parse Failure
## Heartbeat Timeout

---

# STEP 12 — PERFORMANCE OPTIMIZATION

# CRITICAL

Realtime websocket performance affects EVERYTHING later.

---

# REQUIRED OPTIMIZATIONS

## Debounce unnecessary updates
## Avoid giant React rerenders
## Use isolated store selectors
## Prevent event flooding
## Avoid direct component websocket subscriptions

---

# IMPORTANT

WebSocket layer MUST remain:
- lightweight
- non-blocking
- scalable

---

# STEP 13 — MEMORY SAFETY

Need:
- proper cleanup
- event listener removal
- socket disposal
- reconnect cleanup

---

# CRITICAL

Prevent:
- zombie sockets
- duplicate listeners
- stale intervals
- memory leaks

---

# STEP 14 — FUTURE-COMPATIBILITY REQUIREMENTS

Architecture MUST support future:

## Multi-symbol streams
## Options chain streaming
## Replay system
## Multi-chart layouts
## Order execution streams
## ML streams

---

# THEREFORE

WebSocket layer MUST remain:
- modular
- scalable
- loosely coupled

---

# REQUIRED TESTING

Agent MUST perform:

# TEST 1
Initial websocket connection

# TEST 2
Realtime event ingestion

# TEST 3
Auto reconnect after disconnect

# TEST 4
Browser refresh recovery

# TEST 5
Malformed packet handling

# TEST 6
Multiple tab behavior

# TEST 7
Memory leak inspection

# TEST 8
Long-running websocket stability

# TEST 9
Connection timeout simulation

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- websocket lifecycle
- reconnect lifecycle
- event dispatch flow
- store integration flow

---

# B. FILE-BY-FILE IMPLEMENTATION

For EVERY file:
- exact location
- purpose
- integration details

---

# C. FULL PRODUCTION CODE

Need:
- actual implementation
- scalable architecture
- no pseudo code

---

# D. PERFORMANCE OBSERVATIONS

Need:
- websocket latency
- reconnect timing
- memory observations
- event throughput

---

# E. TEST RESULTS

Need proof of:
- reconnect handling
- stable streaming
- event dispatch
- cleanup handling
- websocket resilience

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ Stable websocket connection established  
✅ Auto reconnect works correctly  
✅ No reconnect storms  
✅ Events dispatch to store successfully  
✅ No duplicate websocket connections  
✅ Heartbeat detection functional  
✅ Malformed packets handled safely  
✅ Connection states tracked properly  
✅ Cleanup handling works  
✅ Frontend stable under long-running streaming  
✅ Architecture scalable for future phases  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- replay system
- BOS overlays
- order execution streams
- ML streaming
- multi-symbol multiplexing

Wait for architecture review before proceeding to:
```text
05_MARKET_STATE_MANAGEMENT.md
```