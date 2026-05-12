#!/bin/bash
set -x
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
echo "=== Stopping old containers and cleaning up ==="
docker ps --format "{{.Names}}" | grep "^box5-" | xargs -r docker rm -f 2>/dev/null || true

echo ""
echo "=== Building box5-server image with SSH ==="
if ! docker images | grep -q "box5-server.*latest"; then
    echo "Building box5-server:latest..."
    docker build -f Dockerfile.box5 -t box5-server:latest . || {
        echo "ERROR: Failed to build box5-server image"
        exit 1
    }
    echo "box5-server image built successfully"
else
    echo "box5-server image already exists, rebuilding to include SSH..."
    docker build -f Dockerfile.box5 -t box5-server:latest . || {
        echo "ERROR: Failed to rebuild box5-server image"
        exit 1
    }
fi

echo ""
echo "=== Starting server ==="
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 5

cleanup() {
    echo "=== Stopping server (PID: $SERVER_PID) ==="
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "=== Cleaning up containers ==="
    docker ps --format "{{.Names}}" | grep "^box5-" | xargs -r docker rm -f 2>/dev/null || true
    echo "=== Done ==="
}
trap cleanup EXIT

echo ""
echo "=== Running unit tests ==="
python3 -m pytest tests/test_main.py -v

echo ""
echo "=== Testing user registration (creates container with SSH) ==="
python3 -c "
import requests
import time

# Wait for server
for i in range(10):
    try:
        r = requests.get('http://localhost:8000/login')
        if r.status_code == 200:
            break
    except:
        pass
    time.sleep(1)

# Register a test user
session = requests.Session()
resp = session.post('http://localhost:8000/register', data={
    'username': 'sshtest',
    'password': 'testpass123'
}, allow_redirects=False)

print(f'Register status: {resp.status_code}')

# Wait for container to start
time.sleep(15)

# Check container status
import docker
client = docker.from_env()
try:
    container = client.containers.get('box5-sshtest')
    print(f'Container status: {container.status}')
    print(f'Container ports: {container.ports}')
except Exception as e:
    print(f'Container error: {e}')

# Check SSH port
import os
import glob
upload_dir = os.path.join(os.path.dirname(os.path.abspath('main.py')), 'uploads')
ssh_port_file = os.path.join(upload_dir, 'sshtest', '.ssh_port')
if os.path.exists(ssh_port_file):
    with open(ssh_port_file) as f:
        ssh_port = f.read().strip()
    print(f'SSH port from file: {ssh_port}')
else:
    print('SSH port file not found')

    # List uploads dir
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath('main.py')), 'uploads')
    if os.path.exists(uploads_dir):
        print(f'Uploads dir contents: {os.listdir(uploads_dir)}')
    ssh_dir = os.path.join(uploads_dir, 'sshtest')
    if os.path.exists(ssh_dir):
        print(f'User dir contents: {os.listdir(ssh_dir)}')
"

echo ""
echo "=== Testing SSH connection ==="
python3 -c "
import os
import time
import socket

upload_dir = os.path.join(os.path.dirname(os.path.abspath('main.py')), 'uploads')
ssh_port_file = os.path.join(upload_dir, 'sshtest', '.ssh_port')

if os.path.exists(ssh_port_file):
    with open(ssh_port_file) as f:
        ssh_port = int(f.read().strip())
    print(f'Testing SSH connection to port {ssh_port}...')

    for i in range(20):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', ssh_port))
        sock.close()
        if result == 0:
            print(f'SSH port {ssh_port} is OPEN - SSH is ready!')
            break
        print(f'Waiting for SSH... attempt {i+1}/20')
        time.sleep(1)
    else:
        print('SSH port did not open in time')
else:
    print('Could not find SSH port file')
"

echo ""
echo "=== Testing /api/ssh/{username} endpoint ==="
python3 -c "
import requests
resp = requests.get('http://localhost:8000/api/ssh/sshtest')
print(f'SSH API status: {resp.status_code}')
print(f'SSH API response: {resp.json()}')
"

echo ""
echo "=== All SSH tests completed ==="
