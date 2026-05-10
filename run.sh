#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

unset VIRTUAL_ENV

echo "Starting box5..."

VENV_PYTHON="$HOME/.venv/bin/python"
export SQL5_BINARY="$HOME/.cache/sql5/sql5-macos-arm64"

echo "=== Starting Server on port 3111 ==="
cd Server && $VENV_PYTHON -m uvicorn main:app --port 3111 &
SERVER_PID=$!
cd "$SCRIPT_DIR"

echo "=== Starting Website on port 3112 ==="
cd Website && $VENV_PYTHON -m uvicorn main:app --port 3112 &
WEBSITE_PID=$!
cd "$SCRIPT_DIR"

echo "=== Waiting for services to start ==="
sleep 8

echo "=== Starting Client sync ==="
$VENV_PYTHON -m Client.main --username ccc --password cccpass --folder ./sync &
CLIENT_PID=$!

echo ""
echo "Server: http://localhost:3111"
echo "Website: http://localhost:3112"
echo ""
echo "Server PID: $SERVER_PID"
echo "Website PID: $WEBSITE_PID"
echo "Client PID: $CLIENT_PID"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $SERVER_PID $WEBSITE_PID $CLIENT_PID 2>/dev/null" EXIT

wait