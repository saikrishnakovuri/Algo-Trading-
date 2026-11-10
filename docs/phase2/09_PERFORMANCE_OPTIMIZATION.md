# 09_PERFORMANCE_OPTIMIZATION.md

## Optimization Targets
- React `memo` for chart components.
- Throttle WebSocket message processing (e.g., 60fps frame rate).
- Avoid excessive rerenders.
# 09_PERFORMANCE_OPTIMIZATION.md
# PHASE 2 — REALTIME PERFORMANCE OPTIMIZATION ENGINE

# OBJECTIVE

This phase focuses ONLY on:

```text
Optimizing the frontend for professional realtime trading performance
```

This phase determines:
```text
whether the platform scales smoothly
```

OR:
```text
becomes laggy and unstable under live market load
```

IMPORTANT:
This phase DOES NOT:
- build replay engine
- build BOS overlays
- build execution engine
- build ML systems
- build orderflow systems

This phase ONLY optimizes:
- realtime rendering
- websocket processing
- React rendering behavior
- memory efficiency
- chart update throughput
- frontend responsiveness

---

# PRIMARY GOAL

At the end of this phase:

✅ Frontend remains smooth under heavy live streaming  
✅ React rerenders minimized  
✅ WebSocket processing throttled efficiently  
✅ TradingView updates remain low-latency  
✅ CPU usage remains controlled  
✅ Memory usage remains stable  
✅ No websocket event flooding  
✅ No chart FPS degradation  
✅ No unnecessary state propagation  
✅ Frontend architecture scalable for future high-frequency systems  

---

# IMPORTANT ARCHITECTURAL PRINCIPLE

# THIS PHASE IS ABOUT:

```text
render efficiency + event efficiency
```

NOT:
```text
micro-optimizing random code
```

Most realtime systems fail because:
- every tick rerenders entire UI
- websocket floods React
- charts get recreated
- state trees become huge
- memory grows infinitely

This phase MUST prevent all of that.

---

# CRITICAL PERFORMANCE TARGETS

# TARGET FPS

Need:
```text
55–60 FPS
```

under live streaming.

---

# TARGET LATENCY

Need:
```text
sub-100ms frontend update latency
```

for local environments.

---

# TARGET MEMORY

Need:
```text
stable rolling memory usage
```

NO:
```text
continuous memory growth
```

---

# TARGET CPU

Need:
```text
low idle CPU
moderate live-stream CPU
```

NO:
```text
continuous high CPU spikes
```

---

# CRITICAL RULES

# RULE 1

DO NOT:
```text
rerender TradingView chart component on every websocket message
```

---

# RULE 2

DO NOT:
```text
dispatch every websocket event directly into React rendering pipeline
```

Need:
```text
throttling + batching
```

---

# RULE 3

DO NOT:
```text
store massive market histories in frontend memory
```

Need:
```text
rolling retention
```

---

# RULE 4

DO NOT:
```text
subscribe entire components to entire Zustand store
```

Use:
```text
selectors only
```

---

# EXISTING PROJECT CONTEXT

Already completed:
- FastAPI Gateway
- WebSocket frontend layer
- Zustand market store
- TradingView chart engine
- realtime candle rendering
- symbol/timeframe switching
- trading layout system

Current missing piece:
```text
production-grade frontend performance optimization
```

---

# TARGET OPTIMIZATION ARCHITECTURE

# FINAL FLOW

```text
WebSocket Event
        ↓
Throttle Queue
        ↓
Event Normalization
        ↓
Selective Store Updates
        ↓
Selective Component Updates
        ↓
Incremental TradingView Rendering
        ↓
Smooth UI Rendering
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders/files.

Suggested structure:

```text
frontend/src/modules/market/
│
├── performance/
│   ├── RenderOptimizer.ts
│   ├── WebSocketThrottle.ts
│   ├── FrameScheduler.ts
│   ├── MemoryManager.ts
│   ├── EventBatcher.ts
│   ├── SelectorOptimizer.ts
│   ├── PerformanceMonitor.ts
│   ├── RenderProfiler.ts
│   ├── FPSMonitor.ts
│   └── PerformanceUtils.ts
│
├── charts/
├── websocket/
├── store/
└── rendering/
```

---

# STEP 1 — REACT MEMOIZATION STRATEGY

# CRITICAL

React rerenders are the BIGGEST frontend killer in realtime systems.

---

# REQUIRED OPTIMIZATION

Use:
```typescript
React.memo()
```

for:
- TradingChart
- SignalLogPanel
- Sidebar panels
- Watchlist items
- Overlay containers

---

# IMPORTANT

DO NOT:
```text
memoize blindly
```

Memoize ONLY:
- expensive components
- high-frequency components
- stable-prop components

---

# REQUIRED FILE

```text
RenderOptimizer.ts
```

---

# RESPONSIBILITIES

Need:
- memo wrappers
- stable prop references
- shallow comparison strategies

---

# STEP 2 — WEBSOCKET MESSAGE THROTTLING

# FILE

```text
WebSocketThrottle.ts
```

---

# MOST IMPORTANT FILE IN THIS PHASE

This determines:
```text
whether websocket floods destroy the UI
```

---

# PROBLEM

Realtime market streams may generate:
- hundreds of updates/sec
- tick bursts
- candle floods
- signal bursts

React CANNOT safely render all events individually.

---

# REQUIRED SOLUTION

Throttle websocket processing to:

```text
~60fps
```

Equivalent:
```text
~16ms frame intervals
```

---

# REQUIRED FLOW

```text
Incoming WebSocket Events
          ↓
Throttle Queue
          ↓
Frame Scheduler
          ↓
Batched Store Dispatch
          ↓
UI Update
```

---

# IMPORTANT

DO NOT:
```text
drop critical candle updates
```

Need:
```text
latest-state preservation
```

---

# REQUIRED STRATEGY

Use:
```typescript
requestAnimationFrame()
```

OR:
```typescript
16ms scheduler batching
```

---

# STEP 3 — FRAME SCHEDULER

# FILE

```text
FrameScheduler.ts
```

---

# PURPOSE

Synchronize rendering updates with browser paint cycles.

---

# RESPONSIBILITIES

Need:
- frame batching
- update synchronization
- render pacing
- browser paint alignment

---

# IMPORTANT

This prevents:
- render storms
- frame skipping
- UI jank

---

# STEP 4 — EVENT BATCHING ENGINE

# FILE

```text
EventBatcher.ts
```

---

# PURPOSE

Combine multiple websocket updates efficiently.

---

# RESPONSIBILITIES

Need:
- tick batching
- candle batching
- deduplication
- latest-state prioritization

---

# REQUIRED STRATEGY

Example:

```text
100 tick events arrive
↓
Batch them
↓
Dispatch only latest relevant updates
```

---

# IMPORTANT

DO NOT:
```text
dispatch every single tick individually
```

under heavy load.

---

# STEP 5 — SELECTOR OPTIMIZATION

# FILE

```text
SelectorOptimizer.ts
```

---

# CRITICAL

Bad Zustand selectors =
```text
massive rerender storms
```

---

# REQUIRED STRATEGY

Components MUST subscribe ONLY to:
```text
minimal required state
```

---

# EXAMPLE

GOOD:
```typescript
useMarketStore(state => state.latestPrice)
```

BAD:
```typescript
useMarketStore()
```

---

# REQUIRED OPTIMIZATIONS

Need:
- shallow comparisons
- memoized selectors
- isolated subscriptions

---

# STEP 6 — TRADINGVIEW RENDER OPTIMIZATION

# CRITICAL

TradingView charts MUST remain:
```text
incremental
```

---

# REQUIRED STRATEGY

Use:
```typescript
series.update()
```

ONLY for:
- latest candle updates

Use:
```typescript
setData()
```

ONLY for:
- symbol switch
- timeframe switch
- initial load

---

# IMPORTANT

DO NOT:
```text
recreate chart instance unnecessarily
```

---

# STEP 7 — MEMORY MANAGEMENT ENGINE

# FILE

```text
MemoryManager.ts
```

---

# PURPOSE

Prevent uncontrolled frontend memory growth.

---

# RESPONSIBILITIES

Need:
- candle pruning
- tick pruning
- signal pruning
- stale cache cleanup

---

# REQUIRED STRATEGY

Maintain rolling windows.

Example:
```text
Last 2000 candles
Last 1000 ticks
Last 500 signals
```

---

# IMPORTANT

Realtime systems:
```text
grow forever unless constrained
```

---

# STEP 8 — RENDER PROFILING

# FILE

```text
RenderProfiler.ts
```

---

# PURPOSE

Track:
- rerender counts
- component render frequency
- render bottlenecks

---

# RESPONSIBILITIES

Need:
- debug logging
- render timing
- rerender detection

---

# IMPORTANT

Need ability to identify:
```text
components rerendering excessively
```

---

# STEP 9 — FPS MONITOR

# FILE

```text
FPSMonitor.ts
```

---

# PURPOSE

Realtime FPS observation.

---

# RESPONSIBILITIES

Need:
- frame timing
- FPS calculations
- dropped frame detection

---

# TARGET

Need:
```text
55–60fps
```

during live rendering.

---

# STEP 10 — PERFORMANCE MONITOR

# FILE

```text
PerformanceMonitor.ts
```

---

# PURPOSE

Centralized runtime performance monitoring.

---

# RESPONSIBILITIES

Need:
- websocket throughput
- render timings
- memory observations
- reconnect timing
- CPU observations later

---

# REQUIRED METRICS

Need:
- websocket msg/sec
- candle update latency
- render latency
- store update frequency

---

# STEP 11 — LAZY RENDERING STRATEGY

# REQUIRED OPTIMIZATIONS

Need:
- lazy-load heavy panels
- virtualized logs later
- conditional rendering
- deferred hidden panels

---

# IMPORTANT

DO NOT:
```text
render invisible heavy panels continuously
```

---

# STEP 12 — AVOIDING EXCESSIVE RERENDERS

# CRITICAL

Most frontend failures happen HERE.

---

# REQUIRED STRATEGIES

## React.memo
## useCallback
## useMemo
## Zustand selectors
## Stable object references
## Batched updates

---

# IMPORTANT

Avoid:
```text
new object/function creation every render
```

for high-frequency components.

---

# STEP 13 — WEBSOCKET BACKPRESSURE HANDLING

# CRITICAL

Under heavy tick bursts:
```text
frontend can become overloaded
```

Need:
- event queue control
- queue trimming
- latest-event prioritization

---

# REQUIRED STRATEGY

If queue overloaded:
```text
prioritize latest market state
```

NOT:
```text
historical tick perfection
```

---

# STEP 14 — CHART UPDATE PRIORITIZATION

# IMPORTANT

Not all updates are equally important.

Need priority ordering:

# HIGH PRIORITY
- latest candle
- active symbol
- current timeframe

# LOW PRIORITY
- logs
- old signals
- hidden panels

---

# STEP 15 — FUTURE HIGH-FREQUENCY READINESS

Architecture MUST support future:
- multi-symbol streaming
- options chains
- replay engine
- execution engine
- orderflow visualization

---

# THEREFORE

Optimization architecture MUST remain:
- modular
- scalable
- measurable

---

# STEP 16 — DEVTOOLS & DEBUGGING

Need:
- performance debug mode
- websocket metrics
- render metrics
- FPS metrics

---

# IMPORTANT

Future optimization becomes MUCH easier if observability exists now.

---

# REQUIRED TESTING

Agent MUST perform:

# TEST 1
High-frequency websocket stress test

# TEST 2
FPS stability test

# TEST 3
Memory growth test

# TEST 4
Long-running session test

# TEST 5
Render count profiling

# TEST 6
Tick burst simulation

# TEST 7
Rapid symbol switching performance

# TEST 8
WebSocket reconnect under load

# TEST 9
Chart rendering stability

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- throttling strategy
- batching strategy
- rerender prevention strategy
- memory management strategy

---

# B. FILE-BY-FILE IMPLEMENTATION

For EVERY file:
- exact path
- purpose
- optimization role

---

# C. FULL PRODUCTION CODE

Need:
- actual optimization implementation
- scalable architecture
- no pseudo code

---

# D. PERFORMANCE METRICS

Need:
- FPS observations
- websocket throughput
- render latency
- memory usage
- rerender counts

---

# E. PROFILING RESULTS

Need proof of:
- reduced rerenders
- stable FPS
- controlled memory
- smooth rendering under load

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ React rerenders minimized  
✅ WebSocket processing throttled safely  
✅ TradingView rendering remains smooth  
✅ FPS remains stable under load  
✅ Memory usage remains controlled  
✅ No websocket flooding issues  
✅ Store selectors optimized  
✅ Long-running sessions remain stable  
✅ Frontend scalable for future high-frequency systems  
✅ Performance metrics observable and measurable  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- replay engine
- BOS overlays
- execution visualization
- orderflow rendering
- ML rendering systems

Wait for architecture review before proceeding to:
```text
10_ERROR_HANDLING_AND_RECONNECTS.md
```