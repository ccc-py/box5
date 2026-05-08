#!/bin/bash
set -x

cd "$(dirname "$0")"

unset VIRTUAL_ENV

echo "=== Running pytest (unit tests) ==="
uv run pytest tests/test_server.py tests/test_client.py tests/test_sync.py tests/test_website.py -v

echo "=== Running pytest (server API tests) ==="
uv run pytest tests/test_server_api.py -v

echo "=== Running pytest (E2E tests) ==="
uv run pytest tests/test_e2e.py -v

echo "=== All tests completed ==="