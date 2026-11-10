# WEBSOCKET_INTEGRATION_PLAN.md

## Integration Entry Point
- **Client**: React frontend via `useMarketStream` hook.
- **Connection**: `ws://localhost:8001/ws/live`.
- **State**: `useMarketStore` (Zustand).

## Design Pattern
1. Hook establishes connection.
2. Hook receives JSON via schema (Tick, Candle, Signal).
3. Hook dispatches action to Zustand store.
4. UI components select required state for rendering.
