# 06_REALTIME_CANDLE_RENDERING.md

## Strategy
- Initial load of history via REST.
- Streaming updates via WebSocket `candle` events.
- Efficient memory handling (pruning old data).


# 06_REALTIME_CANDLE_RENDERING.md
# PHASE 2 — REALTIME CANDLE RENDERING ENGINE

# OBJECTIVE

This phase focuses ONLY on:

```text
Building the realtime candle rendering and update engine
```

This phase is the:
```text
core realtime visualization pipeline
```

IMPORTANT:
This phase DOES NOT:
- build BOS overlays
- build replay engine
- build execution visualization
- build ML overlays
- build custom candle engine from ticks yet

This phase ONLY builds:
- realtime candle rendering
- historical candle loading
- websocket candle streaming
- efficient candle updates
- memory-safe chart updates

---

# PRIMARY GOAL

At the end of this phase:

✅ Historical candles load correctly  
✅ Live websocket candle updates work  
✅ Candles update smoothly in realtime  
✅ `series.update()` used efficiently  
✅ No full chart rerenders  
✅ Candle lifecycle stable  
✅ Timeframe-aware rendering functional  
✅ Memory usage controlled  
✅ Duplicate candles prevented  
✅ Chart remains smooth under continuous streaming  
✅ Architecture ready for overlays later  

---

# IMPORTANT ARCHITECTURAL PRINCIPLE

# THIS PHASE DETERMINES:

```text
whether the frontend feels professional
```

OR:
```text
laggy and unstable
```

Realtime candle rendering is one of the MOST IMPORTANT parts of the entire platform.

---

# CRITICAL RULES

# RULE 1

DO NOT:
```text
call setData() repeatedly during live updates
```

Use:
```typescript
series.update()
```

ONLY for realtime streaming.

---

# RULE 2

Use:
```typescript
setData()
```

ONLY for:
- initial history load
- symbol switch
- timeframe switch

---

# RULE 3

DO NOT:
```text
rerender the full React component tree on every candle update
```

---

# RULE 4

DO NOT:
```text
store infinite candle history in memory
```

Need:
```text
rolling candle retention
```

---

# EXISTING PROJECT CONTEXT

Already completed:
- FastAPI Market Gateway
- WebSocket frontend layer
- Zustand market store
- TradingView chart engine
- websocket event ingestion

Current missing piece:
```text
professional realtime candle lifecycle management
```

---

# TARGET RENDERING ARCHITECTURE

# FINAL FLOW

```text
REST Historical Load
        ↓
Normalize Candle Data
        ↓
TradingView setData()
        ↓
WebSocket Candle Stream
        ↓
Validate Candle Event
        ↓
Update Existing Candle
OR
Append New Candle
        ↓
series.update()
        ↓
Realtime Chart Rendering
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders/files.

Suggested structure:

```text
frontend/src/modules/market/
│
├── rendering/
│   ├── CandleRenderer.ts
│   ├── CandleLifecycle.ts
│   ├── CandleHistoryLoader.ts
│   ├── CandleStreamProcessor.ts
│   ├── CandleMemoryManager.ts
│   ├── CandleValidation.ts
│   ├── CandleSyncManager.ts
│   └── CandleUtils.ts
│
├── charts/
├── websocket/
├── store/
└── utils/
```

---

# STEP 1 — HISTORICAL CANDLE LOADER

# FILE

```text
CandleHistoryLoader.ts
```

---

# PURPOSE

Load initial chart history from backend REST APIs.

---

# REQUIRED FLOW

```text
Frontend Loads
      ↓
Request Candle History
      ↓
Validate Response
      ↓
Normalize Data
      ↓
Store in Zustand
      ↓
series.setData()
      ↓
Begin Live Streaming
```

---

# REQUIRED API

Need backend endpoint:

```text
/api/candles/history
```

---

# REQUIRED PARAMETERS

Need:
- symbol
- timeframe
- limit
- optional start/end timestamps later

---

# IMPORTANT

Historical data MUST load:
```text
BEFORE websocket streaming starts
```

Otherwise:
- empty charts
- duplicate candles
- missing candles

become common.

---

# STEP 2 — CANDLE DATA NORMALIZATION

# FILE

```text
CandleUtils.ts
```

---

# PURPOSE

Normalize backend candle data into TradingView-compatible format.

---

# REQUIRED FORMAT

TradingView requires:

```typescript
{
  time: number,
  open: number,
  high: number,
  low: number,
  close: number
}
```

---

# RESPONSIBILITIES

Need:
- timestamp conversion
- numeric normalization
- timezone consistency
- duplicate detection

---

# IMPORTANT

ALL candle timestamps MUST remain:
```text
strictly ordered
```

Otherwise:
- rendering glitches
- candle corruption
- broken zooming

will happen.

---

# STEP 3 — REALTIME CANDLE STREAM PROCESSOR

# FILE

```text
CandleStreamProcessor.ts
```

---

# MOST IMPORTANT FILE IN THIS PHASE

This determines:
```text
how professional realtime rendering feels
```

---

# RESPONSIBILITIES

Need:
- websocket candle ingestion
- partial candle updates
- finalized candle handling
- duplicate prevention
- incremental chart updates

---

# REQUIRED FLOW

```text
WebSocket Candle Event
        ↓
Validate Candle
        ↓
Compare Latest Timestamp
        ↓
Update Existing Candle
OR
Append New Candle
        ↓
Update Zustand Store
        ↓
series.update()
```

---

# IMPORTANT

DO NOT:
```text
replace full candle arrays during streaming
```

---

# STEP 4 — PARTIAL VS FINALIZED CANDLES

# CRITICAL CONCEPT

Frontend MUST understand difference between:

# PARTIAL CANDLE
Still forming.

Example:
```text
09:15 candle still active
```

---

# FINALIZED CANDLE
Completed candle.

Example:
```text
09:15 candle closed
09:16 candle started
```

---

# REQUIRED LOGIC

# SAME TIMESTAMP

Update:
```text
latest candle only
```

using:
```typescript
series.update()
```

---

# NEW TIMESTAMP

Append:
```text
new candle
```

---

# STEP 5 — CANDLE LIFECYCLE MANAGEMENT

# FILE

```text
CandleLifecycle.ts
```

---

# PURPOSE

Manage:
- candle transitions
- candle completion
- timeframe boundaries
- candle synchronization

---

# RESPONSIBILITIES

Need:
- current active candle tracking
- candle rollover handling
- timeframe-aware updates

---

# REQUIRED EXAMPLE

# 1-MINUTE CANDLE

```text
09:15:00 → partial updates
09:15:59 → finalized
09:16:00 → new candle
```

---

# IMPORTANT

Prevent:
- duplicate timestamps
- missing candle rollovers
- stale candle rendering

---

# STEP 6 — CANDLE VALIDATION

# FILE

```text
CandleValidation.ts
```

---

# PURPOSE

Prevent corrupted chart state.

---

# REQUIRED VALIDATIONS

Need:
- valid OHLC
- valid timestamps
- increasing time order
- numeric safety
- duplicate rejection

---

# IMPORTANT

Malformed candles WILL happen later.

Need:
```text
defensive validation layer
```

---

# STEP 7 — MEMORY MANAGEMENT

# FILE

```text
CandleMemoryManager.ts
```

---

# CRITICAL

Realtime systems:
```text
grow forever unless controlled
```

---

# RESPONSIBILITIES

Need:
- rolling candle retention
- old candle pruning
- memory-safe chart history

---

# REQUIRED STRATEGY

Keep:
```text
last N candles
```

Example:
```text
2000 candles per timeframe
```

---

# IMPORTANT

DO NOT:
```text
store infinite candle history in browser memory
```

---

# REQUIRED PRUNING FLOW

```text
New Candle Added
      ↓
Check History Limit
      ↓
Remove Oldest Candles
      ↓
Maintain Rolling Window
```

---

# STEP 8 — CHART SERIES SYNCHRONIZATION

# FILE

```text
CandleSyncManager.ts
```

---

# PURPOSE

Synchronize:
- Zustand candle state
- TradingView series state

---

# RESPONSIBILITIES

Need:
- incremental updates
- chart synchronization
- duplicate prevention
- state consistency

---

# IMPORTANT

Store and chart MUST remain:
```text
synchronized at all times
```

---

# STEP 9 — REALTIME RENDER OPTIMIZATION

# CRITICAL

Realtime rendering performance determines:
- FPS
- latency
- browser stability
- replay scalability later

---

# REQUIRED OPTIMIZATIONS

## Incremental updates only
## Avoid full rerenders
## Batch updates if necessary
## Minimize React renders
## Efficient selectors
## Avoid large object cloning

---

# IMPORTANT

TradingView charts should receive:
```text
minimal update payloads
```

ONLY.

---

# STEP 10 — SYMBOL SWITCHING SUPPORT

IMPORTANT:
Full symbol switching comes later.

BUT rendering engine MUST support:
- chart reset
- history replacement
- websocket resync
- cleanup

WITHOUT:
- memory leaks
- stale candles
- duplicate rendering

---

# STEP 11 — TIMEFRAME SWITCHING SUPPORT

Rendering engine MUST support:
- timeframe reset
- candle replacement
- historical reload
- websocket continuation

WITHOUT:
- corrupted chart state
- mixed timeframe candles

---

# STEP 12 — STALE DATA DETECTION

Need:
- websocket stale detection
- missing candle detection
- stream interruption handling

---

# REQUIRED UI STATES

Need:
- reconnecting
- stale market data
- waiting for candles
- loading history

---

# STEP 13 — FUTURE OVERLAY COMPATIBILITY

IMPORTANT:
Overlays NOT implemented now.

BUT rendering engine MUST support future:
- BOS overlays
- CHOCH labels
- FVG zones
- order blocks
- execution markers

---

# THEREFORE

Candle rendering MUST expose:
```text
overlay synchronization hooks
```

---

# STEP 14 — FUTURE REPLAY COMPATIBILITY

Replay NOT implemented now.

BUT architecture MUST support:
- candle stepping
- historical replay
- pause/resume later

---

# THEREFORE

Rendering engine MUST remain:
- event-driven
- deterministic
- replay-safe

---

# REQUIRED TESTING

Agent MUST perform:

# TEST 1
Initial historical candle load

# TEST 2
Realtime candle updates

# TEST 3
Partial candle updates

# TEST 4
Finalized candle transitions

# TEST 5
Long-running candle streaming

# TEST 6
Memory pruning

# TEST 7
Reconnect candle resync

# TEST 8
High-frequency candle stress test

# TEST 9
Chart synchronization test

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- candle lifecycle
- rendering lifecycle
- websocket integration flow
- memory management strategy

---

# B. FILE-BY-FILE IMPLEMENTATION

For EVERY file:
- exact path
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
- FPS observations
- memory observations
- rendering latency
- candle throughput

---

# E. TEST RESULTS

Need proof of:
- realtime rendering
- candle updates
- memory pruning
- stable rendering
- websocket synchronization

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ Historical candles load correctly  
✅ Realtime websocket candle updates work  
✅ Partial candles update smoothly  
✅ Finalized candles append correctly  
✅ `series.update()` used properly  
✅ No full rerender loops  
✅ Candle memory pruning works  
✅ No duplicate candles  
✅ Chart synchronization stable  
✅ Rendering remains smooth under continuous streaming  
✅ Architecture ready for overlays/replay later  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- BOS overlays
- replay system
- execution visualization
- ML overlays
- order block rendering

Wait for architecture review before proceeding to:
```text
07_TIMEFRAME_AND_SYMBOL_SWITCHING.md
```