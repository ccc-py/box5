#!/bin/bash
set -x
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building box5-server image with SSH ==="
docker build -f Dockerfile.box5 -t box5-server:latest . || {
    echo "ERROR: Failed to build box5-server image"
    exit 1
}

echo ""
echo "=== Stopping any existing server on port 8000 ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo ""
echo "=== Cleaning up old ccc container ==="
docker ps --format "{{.Names}}" | grep "^box5-ccc$" | xargs -r docker rm -f 2>/dev/null || true

echo ""
echo "=== Starting k8s server on port 8000 ==="
VENV_PYTHON="$HOME/.venv/bin/python"
[ ! -f "$VENV_PYTHON" ] && VENV_PYTHON="python3"

$VENV_PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

echo ""
echo "Waiting for server to start..."
sleep 5

echo ""
echo "=== Logging in ccc user (creates container with SSH) ==="
curl -s -L -c /tmp/ccc_cookies.txt -b /tmp/ccc_cookies.txt \
    -X POST http://localhost:8000/login \
    -d "username=ccc&password=cccpass" -o /dev/null

echo ""
echo "=== Waiting for ccc container to be ready (25s) ==="
sleep 25

echo ""
echo "=== Getting SSH port for ccc ==="
SSH_PORT=$(cat "$SCRIPT_DIR/uploads/ccc/.ssh_port" 2>/dev/null)
if [ -z "$SSH_PORT" ]; then
    echo "ERROR: SSH port file not found. Check container logs:"
    docker logs box5-ccc 2>&1 | tail -20
    exit 1
fi
echo "SSH port: $SSH_PORT"

echo ""
echo "=== Verifying SSH user exists in container ==="
docker exec box5-ccc cat /etc/shadow | grep ccc || echo "Warning: ccc user may not exist"

echo ""
echo "=== Testing SSH connection ==="
for i in $(seq 1 30); do
    if nc -z localhost $SSH_PORT 2>/dev/null; then
        echo "SSH port $SSH_PORT is OPEN!"
        break
    fi
    echo "Waiting for SSH... attempt $i/30"
    sleep 2
done

echo ""
echo "=================================================="
echo "Server:  http://localhost:8000"
echo "SSH:     ssh ccc@localhost -p $SSH_PORT"
echo "Pass:    cccpass"
echo "=================================================="
echo ""
echo "Press Ctrl+C to stop all services"

cleanup() {
    echo ""
    echo "=== Stopping server (PID: $SERVER_PID) ==="
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "=== Done ==="
}
trap cleanup EXIT

wait
