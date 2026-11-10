# 03_TRADINGVIEW_CHART_ENGINE.md

## Implementation
- Integrate `lightweight-charts`.
- Real-time candle series updates using `series.update()`.
- Efficient data ingestion from the WebSocket stream.

# 03_TRADINGVIEW_CHART_ENGINE.md
# PHASE 2 — TRADINGVIEW REALTIME CHART ENGINE

# OBJECTIVE

This phase focuses ONLY on:

```text
Building the professional realtime chart rendering engine
```

IMPORTANT:
This phase DOES NOT:
- implement BOS overlays yet
- implement replay mode yet
- implement execution visualization yet
- implement PostgreSQL yet
- implement ML visualization yet

This phase ONLY builds:
- TradingView Lightweight Charts integration
- realtime candlestick rendering
- chart lifecycle management
- efficient candle updates
- smooth rendering architecture

---

# PRIMARY GOAL

Transform the frontend from:

```text
static dashboard charts
```

into:

```text
professional realtime trading charts
```

At the end of this phase:

✅ TradingView charts render correctly  
✅ Live candles update smoothly  
✅ `series.update()` used correctly  
✅ Realtime websocket candle ingestion works  
✅ Charts resize responsively  
✅ Zoom/pan functional  
✅ Crosshair functional  
✅ Multiple chart instances supported  
✅ Chart lifecycle stable  
✅ Performance remains smooth under live updates  
✅ Architecture ready for overlays later  

---

# IMPORTANT ARCHITECTURAL PRINCIPLES

# RULE 1

DO NOT rerender the entire chart on every candle update.

Use:
```javascript
series.update()
```

ONLY for latest candle updates.

This is CRITICAL.

---

# RULE 2

DO NOT store full chart objects in React state.

Use:
```text
refs + isolated chart engine
```

---

# RULE 3

DO NOT tightly couple chart rendering with websocket logic.

Architecture MUST remain:

```text
WebSocket Layer
      ↓
Market Store
      ↓
Chart Adapter
      ↓
TradingView Engine
```

---

# RULE 4

DO NOT implement overlays yet.

NO:
- BOS
- CHOCH
- FVG
- liquidity zones

This phase ONLY perfects:
```text
candle rendering infrastructure
```

---

# EXISTING PROJECT CONTEXT

Backend already exists:
- FastAPI Market Gateway
- websocket broadcaster
- live candle events
- event stream architecture

Frontend currently:
- React frontend exists
- Streamlit charts exist
- TradingView charts NOT integrated yet

---

# REQUIRED LIBRARY

Install:

```bash
npm install lightweight-charts
```

OPTIONAL:
```bash
npm install @types/node
```

---

# TARGET ARCHITECTURE

# CHART RENDERING FLOW

```text
FastAPI WebSocket
        ↓
Frontend WebSocket Client
        ↓
Market Store (Zustand)
        ↓
Chart Adapter
        ↓
TradingView Chart
        ↓
Candlestick Series
```

---

# TARGET MODULE STRUCTURE

ONLY create missing folders.

Suggested structure:

```text
frontend/src/modules/market/
│
├── charts/
│   ├── TradingChart.tsx
│   ├── chartConfig.ts
│   ├── chartTheme.ts
│   ├── chartTypes.ts
│   ├── chartUtils.ts
│   ├── CandleSeriesManager.ts
│   └── ChartLifecycle.ts
│
├── websocket/
│
├── store/
│
├── hooks/
│
└── utils/
```

---

# STEP 1 — CHART ENGINE INITIALIZATION

# FILE

```text
TradingChart.tsx
```

---

# RESPONSIBILITIES

This component MUST:
- initialize TradingView chart
- manage chart lifecycle
- create candlestick series
- handle resizing
- cleanup chart safely
- receive market data updates

---

# REQUIRED FEATURES

## Chart Initialization
## Responsive Resize
## Dark Theme
## Candlestick Series
## Crosshair
## Time Scale
## Price Scale
## Cleanup on Unmount

---

# IMPORTANT

Chart object MUST use:
```typescript
useRef()
```

NOT React state.

---

# REQUIRED IMPLEMENTATION PATTERN

Use:

```typescript
const chartRef = useRef<IChartApi | null>(null)
```

and:

```typescript
const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
```

---

# STEP 2 — CHART CONFIGURATION SYSTEM

# FILE

```text
chartConfig.ts
```

---

# PURPOSE

Centralized chart configuration.

---

# CONFIGURATION MUST INCLUDE

## Layout
- dark background
- text colors
- font styles

## Grid
- vertical lines
- horizontal lines

## Crosshair
- mode
- labels

## Price Scale
- margins
- visibility

## Time Scale
- visibility
- spacing

---

# IMPORTANT

DO NOT hardcode config directly inside components.

Need centralized configuration architecture.

---

# STEP 3 — CHART THEME ENGINE

# FILE

```text
chartTheme.ts
```

---

# PURPOSE

Centralized theme management.

Need:
- dark trading theme
- future light theme support
- reusable color tokens

---

# TARGET STYLE

Inspired by:
- TradingView
- Binance
- Zerodha Kite
- Quantower

---

# REQUIRED COLORS

Need:
- bullish candle colors
- bearish candle colors
- grid colors
- background colors
- text colors

---

# IMPORTANT

Theme system MUST remain:
- reusable
- modular
- scalable

---

# STEP 4 — CANDLE DATA TYPES

# FILE

```text
chartTypes.ts
```

---

# PURPOSE

Strong typing for chart data.

---

# REQUIRED TYPES

Need:
- CandleData
- TickData
- Timeframe
- Symbol
- ChartEvent
- ChartState

---

# CANDLE TYPE FORMAT

```typescript
{
  time: number,
  open: number,
  high: number,
  low: number,
  close: number
}
```

IMPORTANT:
Convert backend timestamps properly.

---

# STEP 5 — CHART LIFECYCLE MANAGEMENT

# FILE

```text
ChartLifecycle.ts
```

---

# PURPOSE

Encapsulate:
- chart creation
- destruction
- resizing
- subscriptions
- cleanup

---

# RESPONSIBILITIES

Need:
- resize observers
- memory-safe cleanup
- event unsubscription
- chart disposal

---

# CRITICAL

Prevent:
- memory leaks
- duplicate chart instances
- stale subscriptions

---

# STEP 6 — REALTIME CANDLE UPDATE ENGINE

# FILE

```text
CandleSeriesManager.ts
```

---

# MOST IMPORTANT FILE IN THIS PHASE

This file determines:
```text
whether charts feel professional
```

or:
```text
laggy and amateur
```

---

# RESPONSIBILITIES

Need:
- incremental candle updates
- finalized candle handling
- historical candle loading
- duplicate prevention

---

# REQUIRED UPDATE LOGIC

# PARTIAL CANDLE

Use:
```typescript
series.update()
```

for:
- latest candle changes

---

# FINALIZED CANDLE

Append:
- completed candles
- new timeframe candles

---

# IMPORTANT

DO NOT:
```text
call setData() repeatedly
```

during live streaming.

That destroys performance.

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
series.update()
```

---

# STEP 7 — HISTORICAL DATA LOADING

# PURPOSE

Load initial chart history.

---

# FLOW

```text
Frontend Loads
      ↓
Request Historical Candles
      ↓
Normalize Data
      ↓
series.setData()
      ↓
Start Live Updates
```

---

# IMPORTANT

Use:
```typescript
setData()
```

ONLY:
- initial load
- full symbol switch
- timeframe switch

NOT for live updates.

---

# STEP 8 — RESPONSIVE RESIZE SYSTEM

# PURPOSE

Charts must resize automatically.

---

# IMPLEMENT

Need:
- ResizeObserver
- responsive width/height
- fullscreen support later

---

# IMPORTANT

DO NOT:
```text
hardcode chart dimensions
```

---

# STEP 9 — MULTI-CHART SUPPORT

# FUTURE REQUIREMENT

Architecture MUST support:
- multiple chart instances
- future multi-timeframe layouts
- detached charts later

---

# IMPORTANT

Chart engine MUST remain:
- isolated
- reusable
- instance-safe

---

# STEP 10 — PERFORMANCE OPTIMIZATION

# CRITICAL PHASE

Realtime chart performance is EVERYTHING.

---

# REQUIRED OPTIMIZATIONS

## Avoid rerenders
## Use refs
## Memoize callbacks
## Incremental updates only
## Avoid giant React state trees
## Throttle unnecessary updates

---

# TARGET PERFORMANCE

Need:
- smooth FPS
- low CPU usage
- low memory usage
- stable updates under heavy streaming

---

# STEP 11 — ERROR HANDLING

# HANDLE

Need:
- malformed candles
- invalid timestamps
- missing OHLC
- websocket disconnects
- stale chart instances

---

# REQUIRED UI STATES

Need visible:
- loading history
- reconnecting
- disconnected
- waiting for data

---

# STEP 12 — SYMBOL SWITCHING PREPARATION

IMPORTANT:
Full symbol switching comes later.

BUT chart engine MUST support:
- chart reset
- series cleanup
- historical reload

without memory leaks.

---

# STEP 13 — TIMEFRAME SWITCHING PREPARATION

Chart engine MUST support:
- full series replacement
- historical reload
- clean transition

WITHOUT:
- duplicate candles
- stale chart state

---

# STEP 14 — FUTURE OVERLAY PREPARATION

IMPORTANT:
Overlays NOT implemented now.

BUT architecture MUST allow future:
- BOS lines
- CHOCH labels
- FVG rectangles
- liquidity zones
- execution markers

---

# THEREFORE

Chart engine MUST expose:
```text
overlay attachment points
```

---

# REQUIRED TESTING

Agent MUST test:

# TEST 1
Realtime candle streaming

# TEST 2
Continuous websocket updates

# TEST 3
High-frequency updates

# TEST 4
Resize handling

# TEST 5
Unmount/remount cleanup

# TEST 6
Symbol reload preparation

# TEST 7
Memory leak inspection

# TEST 8
FPS stability observation

---

# REQUIRED OUTPUTS

Agent MUST provide:

# A. ARCHITECTURE REPORT

Need:
- chart rendering lifecycle
- update flow
- websocket integration flow
- performance strategy

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
- no pseudo code
- scalable architecture

---

# D. PERFORMANCE OBSERVATIONS

Need:
- FPS observations
- memory observations
- rerender analysis
- websocket rendering latency

---

# E. TEST RESULTS

Need proof of:
- realtime rendering
- candle updates
- resize handling
- cleanup handling
- stable chart lifecycle

---

# SUCCESS CRITERIA

This phase is COMPLETE ONLY IF:

✅ TradingView chart renders correctly  
✅ Candlestick series works  
✅ Realtime candles update smoothly  
✅ `series.update()` used properly  
✅ Historical candles load correctly  
✅ No full rerender loops  
✅ Chart resizes correctly  
✅ Crosshair functional  
✅ Zoom/pan functional  
✅ Memory leaks absent  
✅ Chart cleanup works  
✅ Frontend remains stable under live streaming  
✅ Architecture ready for overlays later  

---

# IMPORTANT FINAL INSTRUCTION

After completing this phase:

STOP.

DO NOT implement:
- BOS overlays
- replay system
- execution visualization
- ML overlays
- order blocks
- liquidity zones

Wait for architecture review before proceeding to:
```text
04_WEBSOCKET_FRONTEND_LAYER.md
```