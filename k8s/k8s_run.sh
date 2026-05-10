#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

unset VENV_PYTHON

echo "Starting box5 k8s version..."

echo "=== Stopping any existing server on port 8000 ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

docker ps --format "{{.Names}}" | grep "box5-k8s" | xargs -r docker rm -f 2>/dev/null || true

VENV_PYTHON="$HOME/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

echo "=== Starting Box5 K8s Web Server on port 8000 ==="
$VENV_PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

echo ""
echo "Website: http://localhost:8000"
echo ""
echo "Server PID: $SERVER_PID"
echo ""
echo "Press Ctrl+C to stop the server"

trap "kill $SERVER_PID 2>/dev/null" EXIT

wait