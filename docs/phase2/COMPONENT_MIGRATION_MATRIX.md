# COMPONENT_MIGRATION_MATRIX.md

| Component | Status | Action | Notes |
|---|---|---|---|
| Streamlit Charts | Replace | TradingView | Not realtime, high latency |
| Telegram Bot Admin | Keep | As-Is | Retained in React |
| Market Data Panel | Replace | WebSocket/Zustand | Needs real-time stream |
| Trade Reporting | Keep | Streamlit | Well-suited for static reports |
| Realtime Charts | New | TradingView | Required for trading |
| System Status | Modify | API Hook | Link to new Gateway |
| Order Entry | Modify | API Hook | Upgrade for low latency |
