# Frontend Notice

This directory (`frontend/`) contains an optional standalone Vite/React dashboard client.

**Active Production Dashboard**:
The production-ready, fully responsive surveillance HUD dashboard is served directly by FastAPI at `/` and `/dashboard` from `backend/app/static/index.html`. It runs with zero Node.js/npm dependencies, works across Chrome, Safari, Firefox, Edge, and iOS/Android mobile viewports, and connects directly to the live MJPEG stream and WebSocket telemetry.
