#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Running pytest tests..."
python3 -m pytest test_main.py -v
echo ""
echo "All tests passed!"