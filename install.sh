#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Installing box5 dependencies ==="

echo "Installing Python dependencies with uv..."
uv sync

echo "Installing additional dependencies..."
uv pip install jinja2 websocket-client websockets

echo "Installing playwright for E2E tests..."
~/.venv/bin/python -m playwright install chromium

echo "=== Install complete ==="