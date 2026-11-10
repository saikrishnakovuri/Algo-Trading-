# ROUTING_MIGRATION_PLAN.md

## Existing Routes
- Root/Admin: Primarily handled by Streamlit.
- App Routes: Likely handled by React Router (to be audited).

## Proposed Routes
- `/dashboard`: Streamlit (Analytics)
- `/trade`: React (Realtime Charting)
- `/alerts`: React (Live Signal Log)
- `/settings`: React (Trading Config)
- `/logs`: Streamlit (Admin/Debug)
