import pytest
import requests
import time
import subprocess
import os
import signal
import sys
import pathlib

SERVER_URL = "http://localhost:3111"
WEBSITE_URL = "http://localhost:3112"

@pytest.fixture(scope="module", autouse=True)
def start_servers():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    venv_python = os.path.join(project_dir, ".venv", "bin", "python")
    sql5_binary = str(pathlib.Path.home() / ".cache" / "sql5" / "sql5-macos-arm64")
    env = {**os.environ, "PYTHONPATH": project_dir, "SQL5_BINARY": sql5_binary}

    server_code = f"""
import sys
sys.path.insert(0, '{project_dir}')
from Server.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=3111)
"""
    website_code = f"""
import sys
sys.path.insert(0, '{project_dir}')
from Website.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=3112)
"""

    server_proc = subprocess.Popen(
        [venv_python, "-c", server_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
        cwd=project_dir
    )
    website_proc = subprocess.Popen(
        [venv_python, "-c", website_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={**env, "SERVER_URL": SERVER_URL},
        start_new_session=True,
        cwd=project_dir
    )

    time.sleep(8)

    if server_proc.poll() is not None:
        _, stderr = server_proc.communicate()
        print(f"Server failed to start: {stderr.decode()}")

    yield

    server_proc.terminate()
    website_proc.terminate()
    server_proc.wait()
    website_proc.wait()

@pytest.fixture(scope="module")
def api_user():
    return {"username": "apiuser", "password": "apipass123"}

def test_server_health():
    resp = requests.get(f"{SERVER_URL}/docs", allow_redirects=False)
    assert resp.status_code in [200, 307, 302]

def test_register_user(api_user):
    requests.post(
        f"{SERVER_URL}/api/register",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    resp = requests.post(
        f"{SERVER_URL}/api/register",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    assert resp.status_code == 400

def test_login_user(api_user):
    requests.post(
        f"{SERVER_URL}/api/register",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

def test_login_invalid_credentials():
    resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": "nonexistent", "password": "wrongpass"}
    )
    assert resp.status_code == 401

def test_file_upload_with_auth(api_user):
    requests.post(
        f"{SERVER_URL}/api/register",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    login_resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    token = login_resp.json()["access_token"]
    
    files = {"file": ("test_upload.txt", b"Hello World", "text/plain")}
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{SERVER_URL}/api/files/upload", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test_upload.txt"

def test_file_list_with_auth(api_user):
    login_resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{SERVER_URL}/api/files", headers=headers)
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list)

def test_file_list_without_auth():
    resp = requests.get(f"{SERVER_URL}/api/files")
    assert resp.status_code in [401, 403]

def test_public_files():
    resp = requests.get(f"{SERVER_URL}/api/public/files")
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list)

def test_folder_files(api_user):
    login_resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    token = login_resp.json()["access_token"]
    
    files = {"file": ("folder_test.txt", b"test", "text/plain")}
    data = {"folder": "testfolder"}
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{SERVER_URL}/api/files/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 200
    
    resp = requests.get(f"{SERVER_URL}/api/files?folder=testfolder", headers=headers)
    assert resp.status_code == 200
    files = resp.json()
    assert any(f["folder"] == "testfolder" for f in files)

def test_subfolders(api_user):
    login_resp = requests.post(
        f"{SERVER_URL}/api/login",
        json={"username": api_user["username"], "password": api_user["password"]}
    )
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{SERVER_URL}/api/files/subfolders", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "subfolders" in data

def test_terminal_websocket():
    import websockets
    import asyncio
    import json

    async def run_test():
        uri = f"ws://localhost:3111/ws/editor"
        try:
            async with websockets.connect(uri) as ws:
                # Init shell
                await ws.send('<message type="terminal_input"><command></command><cwd>./</cwd></message>')
                
                # Consume prompt
                for _ in range(5):
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        break
                        
                # Send raw data
                data_json = json.dumps("ls\r")
                req = f'<message type="terminal_input"><raw_data>{data_json}</raw_data></message>'
                await ws.send(req)
                
                # Check response
                res = await asyncio.wait_for(ws.recv(), timeout=2.0)
                assert res is not None
                
                # Send exit
                await ws.send('<message type="terminal_input"><command>exit</command></message>')
        except Exception as e:
            pytest.fail(f"WebSocket test failed: {e}")

    asyncio.run(run_test())