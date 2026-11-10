# 07_TIMEFRAME_AND_SYMBOL_SWITCHING.md

## Implementation
- UI dropdown for timeframe and symbol.
- Trigger API call to fetch new history.
- Subscribe to new WebSocket symbol channel.


# 07_TIMEFRAME_AND_SYMBOL_SWITCHING.md
# PHASE 2 — TIMEFRAME & SYMBOL SWITCHING ENGINE

# OBJECTIVE

This phase focuses ONLY on:

```text
Building professional symbol and timeframe switching behavior
```

This phase transforms the frontend from:
```text
single-stream static chart
```

into:
```text
interactive trading terminal
```

IMPORTANT:
This phase DOES NOT:
- build replay engine
- build BOS overlays
- build execution visualization
- build ML overlays
- build options chain multiplexing yet

This phase ONLY builds:
- symbol switching
- timeframe switching
- historical reload orchestration
- websocket resubscription logic
- chart reset lifecycle
- synchronized market transitions

---

# PRIMARY GOAL

At the end of this phase:

✅ Users can switch symbols dynamically  
✅ Users can switch timeframes dynamically  
✅ Chart reloads correctly  
✅ Historical candles reload correctly  
✅ WebSocket stream updates correctly  
✅ No stale candles remain  
✅ No duplicate subscriptions occur  
✅ No memory leaks occur  
✅ UI transitions remain smooth  
✅ TradingView rendering stays synchronized  
✅ Architecture scalable for future multi-symbol support  

---

# IMPORTANT ARCHITECTURAL PRINCIPLE

# THIS PHASE IS ABOUT:

```text
state synchronization
```

NOT:
```text
simple dropdown UI
```

Most trading UIs fail here because:
- stale websocket streams remain alive
- old candles remain cached
- timeframe data mixes incorrectly
- charts desynchronize
- duplicate events occur

This phase MUST prevent all of that.

---

# CRITICAL RULES

# RULE 1

DO NOT:
```text
reload entire frontend page on symbol switch
```

Everything MUST remain:
```text
realtime and seamless
```

---

# RULE 2

DO NOT:
```text
open a new websocket connection per symbol
```

Reuse centralized websocket architecture.

---

# RULE 3

DO NOT:
```text
mix candles from different symbols/timeframes
```

Need:
```text
strict synchronization logic
```

---

# RULE 4

DO NOT:
```text
rerender TradingView chart from scratch unnecessarily
```

Reuse chart instance safely.

---

# EXISTING PROJECT CONTEXT

Already completed:
- FastAPI Market Gateway
- WebSocket frontend layer
- Zustand market store
- TradingView chart engine
- realtime candle rendering

Current missing piece:
```text
interactive market navigation system
```

---

# TARGET ARCHITECTURE

# FINAL FLOW

```text
User Changes Symbol/Timeframe
            ↓
Update Market Store
            ↓
Pause Current Stream
            ↓
Fetch Historical Candles
            ↓
Reset Candle State
            ↓
Update TradingView Series
            ↓
Resubscribe WebSocket Stream
            ↓
Resume Live Rendering
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders/files.

Suggested structure:

```text
frontend/src/modules/market/
│
├── switching/
│   ├── SymbolManager.ts
│   ├── TimeframeManager.ts
│   ├── StreamSubscriptionManager.ts
│   ├── ChartResetManager.ts
│   ├── MarketTransitionManager.ts
│   ├── SwitchingValidation.ts
│   ├── SwitchingUtils.ts
│   └── SwitchingTypes.ts
│
├── components/
│   ├── SymbolSelector.tsx
│   ├── TimeframeSelector.tsx
│   └── MarketToolbar.tsx
│
├── websocket/
├── rendering/
├── store/
└── utils/
```

---

# STEP 1 — SYMBOL SELECTOR UI

# FILE

```text
SymbolSelector.tsx
```

---

# PURPOSE

Allow user to dynamically switch market instruments.

---

# REQUIRED SYMBOLS

Initially support:

```text
NIFTY
BANKNIFTY
FINNIFTY
```

Architecture MUST support future:
- equities
- options
- crypto
- forex

---

# REQUIRED FEATURES

## Dropdown UI
## Active symbol highlight
## Loading state
## Transition state
## Error state

---

# IMPORTANT

UI MUST remain:
```text
non-blocking
```

during reloads.

---

# STEP 2 — TIMEFRAME SELECTOR UI

# FILE

```text
TimeframeSelector.tsx
```

---

# REQUIRED TIMEFRAMES

Need:

```text
1m
5m
15m
1h
4h
1D
```

Architecture MUST support future:
- custom timeframes
- tick charts
- second charts

---

# REQUIRED FEATURES

## Active timeframe highlight
## Instant switching
## Responsive layout
## Loading feedback

---

# STEP 3 — SWITCHING STATE TYPES

# FILE

```text
SwitchingTypes.ts
```

---

# PURPOSE

Centralized typing for:
- symbol state
- timeframe state
- transition state
- subscription state

---

# REQUIRED TYPES

Need:
- Symbol
- Timeframe
- SwitchingState
- TransitionStatus

---

# STEP 4 — MARKET TRANSITION MANAGER

# FILE

```text
MarketTransitionManager.ts
```

---

# MOST IMPORTANT FILE IN THIS PHASE

This determines:
```text
whether switching feels professional
```

or:
```text
buggy and unstable
```

---

# RESPONSIBILITIES

Need:
- coordinated transitions
- state synchronization
- chart synchronization
- websocket synchronization
- loading orchestration

---

# REQUIRED FLOW

# SYMBOL SWITCH

```text
User Changes Symbol
        ↓
Pause Live Updates
        ↓
Clear Current Candle Stream
        ↓
Fetch Historical Data
        ↓
Reset Chart Series
        ↓
Load New Candles
        ↓
Resubscribe WebSocket
        ↓
Resume Rendering
```

---

# TIMEFRAME SWITCH

```text
User Changes Timeframe
        ↓
Pause Rendering
        ↓
Fetch New Timeframe History
        ↓
Replace Candle Dataset
        ↓
Resubscribe Stream
        ↓
Resume Live Updates
```

---

# IMPORTANT

Switching MUST remain:
```text
atomic
```

Prevent:
- mixed candles
- stale websocket updates
- partially updated charts

---

# STEP 5 — SYMBOL MANAGER

# FILE

```text
SymbolManager.ts
```

---

# PURPOSE

Centralized symbol state orchestration.

---

# RESPONSIBILITIES

Need:
- active symbol tracking
- symbol validation
- symbol switching actions
- symbol cache handling

---

# REQUIRED ACTIONS

Need:
- setActiveSymbol()
- clearSymbolState()
- preloadSymbolData()

---

# STEP 6 — TIMEFRAME MANAGER

# FILE

```text
TimeframeManager.ts
```

---

# PURPOSE

Centralized timeframe orchestration.

---

# RESPONSIBILITIES

Need:
- timeframe switching
- timeframe validation
- timeframe synchronization

---

# REQUIRED ACTIONS

Need:
- setActiveTimeframe()
- reloadTimeframeData()
- resetTimeframeState()

---

# STEP 7 — STREAM SUBSCRIPTION MANAGER

# FILE

```text
StreamSubscriptionManager.ts
```

---

# CRITICAL

This manages:
```text
websocket subscription synchronization
```

---

# RESPONSIBILITIES

Need:
- unsubscribe old stream
- subscribe new stream
- prevent duplicate subscriptions
- synchronize active stream state

---

# REQUIRED FLOW

```text
Old Symbol Active
       ↓
Unsubscribe Old Channel
       ↓
Clear Stream State
       ↓
Subscribe New Channel
       ↓
Resume Updates
```

---

# IMPORTANT

DO NOT:
```text
leave stale websocket listeners alive
```

That causes:
- duplicate candles
- duplicated events
- memory leaks

---

# STEP 8 — CHART RESET MANAGER

# FILE

```text
ChartResetManager.ts
```

---

# PURPOSE

Safely reset TradingView series during switching.

---

# RESPONSIBILITIES

Need:
- clear old candles
- load new candles
- preserve chart instance
- maintain smooth transitions

---

# IMPORTANT

DO NOT:
```text
destroy/recreate full chart unnecessarily
```

Reuse:
```text
existing chart instance
```

ONLY replace:
```text
series data
```

---

# STEP 9 — HISTORICAL DATA RELOAD

# REQUIRED FLOW

```text
Switch Triggered
      ↓
REST API Call
      ↓
Load Historical Candles
      ↓
Normalize Candles
      ↓
Replace Current Store Candles
      ↓
Update TradingView setData()
```

---

# IMPORTANT

Historical reload MUST finish:
```text
BEFORE live websocket updates resume
```

Otherwise:
- duplicate candles
- stale rendering
- missing candles

become common.

---

# STEP 10 — WEBSOCKET RESUBSCRIPTION

# REQUIRED FLOW

```text
Switch Triggered
       ↓
Unsubscribe Current Stream
       ↓
Wait For Confirmation
       ↓
Subscribe New Stream
       ↓
Resume Event Processing
```

---

# IMPORTANT

Prevent:
- old symbol events leaking
- mixed timeframe events
- duplicate websocket processing

---

# STEP 11 — LOADING & TRANSITION STATES

# REQUIRED UI STATES

Need:
- loading history
- switching symbol
- switching timeframe
- reconnecting stream
- stream synchronized
- stream failed

---

# IMPORTANT

User MUST always know:
```text
what state the terminal is in
```

---

# STEP 12 — SWITCHING VALIDATION

# FILE

```text
SwitchingValidation.ts
```

---

# PURPOSE

Prevent invalid transitions.

---

# REQUIRED VALIDATIONS

Need:
- valid symbol
- valid timeframe
- valid websocket subscription
- synchronized chart state
- no duplicate transitions

---

# IMPORTANT

Rapid switching WILL happen later.

Need:
```text
transition locking
```

to prevent race conditions.

---

# STEP 13 — MEMORY SAFETY

# CRITICAL

Need:
- old candle cleanup
- stale stream cleanup
- old subscription cleanup
- transition cleanup

---

# IMPORTANT

Prevent:
- stale listeners
- orphan websocket handlers
- old symbol candle retention

---

# STEP 14 — PERFORMANCE OPTIMIZATION

# CRITICAL

Switching MUST feel:
```text
instant and smooth
```

---

# REQUIRED OPTIMIZATIONS

## Reuse chart instance
## Reuse websocket connection
## Incremental updates
## Efficient selector usage
## Avoid full React rerenders

---

# IMPORTANT

DO NOT:
```text
reload the entire application
```

for market switching.

---

# STEP 15 — FUTURE MULTI-SYMBOL COMPATIBILITY

IMPORTANT:
Multi-symbol layouts NOT implemented now.

BUT architecture MUST support future:
- watchlists
- multi-chart layouts
- options chains
- detached windows

---

# THEREFORE

Switching engine MUST remain:
- modular
- scalable
- subscription-aware

---

# STEP 16 — FUTURE REPLAY COMPATIBILITY

Replay NOT implemented now.

BUT switching system MUST support:
- replay symbol changes
- replay timeframe changes
- replay synchronization later

---

# REQUIRED TESTING

Agent MUST perform:

# TEST 1
Symbol switching

# TEST 2
Timeframe switching

# TEST 3
Rapid switching stress test

# TEST 4
WebSocket resubscription

# TEST 5
Chart synchronization

# TEST 6
Memory cleanup validation

# TEST 7
Stale stream prevention

# TEST 8
Reconnect during switching

# TEST 9
Transition state handling

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- switching lifecycle
- websocket resubscription flow
- chart reset flow
- synchronization strategy

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
- switching latency
- render smoothness
- websocket synchronization timing
- memory observations

---

# E. TEST RESULTS

Need proof of:
- smooth switching
- websocket resubscription
- no stale candles
- no duplicate streams
- stable rendering

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ Symbol switching works correctly  
✅ Timeframe switching works correctly  
✅ Historical reloads work  
✅ WebSocket resubscription works  
✅ No duplicate subscriptions occur  
✅ No stale candles remain  
✅ TradingView chart stays synchronized  
✅ Memory cleanup works  
✅ Switching remains smooth under rapid usage  
✅ Architecture scalable for future multi-symbol layouts  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- BOS overlays
- replay engine
- multi-chart layouts
- options chains
- execution visualization

Wait for architecture review before proceeding to:
```text
08_UI_UX_TRADING_LAYOUT.md
```