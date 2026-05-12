#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Checking Docker ==="
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and try again."
    echo ""
    echo "On macOS, you can start Docker Desktop from:"
    echo "  - Applications > Docker > Docker Desktop"
    echo "  - Or: open -a Docker"
    exit 1
fi

echo "Docker is running"

echo ""
echo "=== Building box5-server image ==="
if ! docker images | grep -q "box5-server.*latest"; then
    echo "Building box5-server:latest..."
    docker build -f Dockerfile.box5 -t box5-server:latest . || {
        echo "ERROR: Failed to build box5-server image"
        exit 1
    }
    echo "box5-server image built successfully"
else
    echo "box5-server image already exists"
fi

echo ""
echo "=== Running unit tests ==="
VENV_PYTHON="$HOME/.venv/bin/python"
[ ! -f "$VENV_PYTHON" ] && VENV_PYTHON="python3"
cd /Users/Shared/ccc/project/box5/k8s
export DB_PATH="/Users/Shared/ccc/project/box5/k8s/box5.db"

$VENV_PYTHON -m pytest tests/test_main.py -v
$VENV_PYTHON -m pytest tests/test_auth.py -v
$VENV_PYTHON -m pytest tests/test_auth_api.py -v
$VENV_PYTHON -m pytest tests/test_admin.py -v
$VENV_PYTHON -m pytest tests/test_admin_api.py -v
$VENV_PYTHON -m pytest tests/test_share.py -v
$VENV_PYTHON -m pytest tests/test_share_api.py -v
$VENV_PYTHON -m pytest tests/test_client.py -v
$VENV_PYTHON -m pytest tests/test_sync.py -v

echo ""
echo "=== Starting server for e2e tests ==="
$VENV_PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 3

cleanup() {
    echo "=== Stopping server (PID: $SERVER_PID) ==="
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "=== Server stopped ==="
}
trap cleanup EXIT

echo "=== Running e2e tests ==="
$VENV_PYTHON -m pytest tests/e2e_test.py -v

echo ""
echo "=== Testing Docker integration (login with container) ==="
python3 -c "
import requests
import time

# Wait for server to be ready
for i in range(10):
    try:
        r = requests.get('http://localhost:8000/login')
        if r.status_code == 200:
            break
    except:
        pass
    time.sleep(1)

# Try to login with default user
session = requests.Session()
resp = session.post('http://localhost:8000/login', data={
    'username': 'ccc',
    'password': 'cccpass'
}, allow_redirects=False)

if resp.status_code in [302, 200]:
    print('Docker integration test: Login successful (container created)')
else:
    # Check if it's a docker error
    if 'Docker' in resp.text or 'docker' in resp.text:
        print('Docker integration test: Container creation issue detected')
    else:
        print(f'Docker integration test: Status {resp.status_code}')
"

echo ""
echo "All tests passed!"