#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo " AI Road Damage Detection and Real-Time Object Recognition System"
echo "=============================================================================="

if [ -d "venv" ]; then
    UVICORN="./venv/bin/uvicorn"
else
    UVICORN="uvicorn"
fi

PORT="${PORT:-7860}"
echo "Starting AI Surveillance Server on 0.0.0.0:${PORT} ..."
exec $UVICORN main:app --app-dir backend --host 0.0.0.0 --port "$PORT"
