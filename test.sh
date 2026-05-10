#!/bin/bash
set -x

cd "$(dirname "$0")"

unset VIRTUAL_ENV

VENV_PYTHON="$HOME/.venv/bin/python"

echo "=== Running pytest (unit tests) ==="
$VENV_PYTHON -m pytest tests/test_server.py tests/test_client.py tests/test_sync.py tests/test_website.py -v

echo "=== Running pytest (server API tests) ==="
$VENV_PYTHON -m pytest tests/test_server_api.py -v

echo "=== Running pytest (E2E tests) ==="
$VENV_PYTHON -m pytest tests/test_e2e.py -v

echo "=== All tests completed ==="