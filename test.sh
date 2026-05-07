#!/bin/bash
set -x

cd "$(dirname "$0")"

echo "=== Running pytest ==="
python -m pytest tests/ -v

echo "=== All tests completed ==="