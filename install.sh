#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Installing box5 dependencies ==="

echo "Installing Python dependencies with uv..."
uv sync

echo "Installing additional dependencies..."
uv pip install --python .venv/bin/python jinja2 websocket-client

echo "Installing playwright for E2E tests..."
uv run playwright install chromium

find_old_venv() {
    for venv_path in "$HOME/venv" "/Users/cccuser/venv" "$HOME/.venv"; do
        if [ -d "$venv_path/lib/python3.12/site-packages/sql5" ]; then
            echo "$venv_path"
            return 0
        fi
    done
    return 1
}

OLD_VENV_BASE=$(find_old_venv)
if [ -n "$OLD_VENV_BASE" ]; then
    echo "Found old venv at $OLD_VENV_BASE, copying sql5..."
    mkdir -p .venv/lib/python3.11/site-packages/
    cp -r "$OLD_VENV_BASE/lib/python3.12/site-packages/sql5" .venv/lib/python3.11/site-packages/
    cp -r "$OLD_VENV_BASE/lib/python3.12/site-packages/sql5-3.5.0.dist-info" .venv/lib/python3.11/site-packages/
    echo "sql5 copied"
elif [ -d "$HOME/.cache/sql5" ]; then
    echo "Using existing sql5 from ~/.cache/sql5"
else
    echo "Warning: sql5 not found. It will be downloaded on first run."
fi

echo "=== Install complete ==="