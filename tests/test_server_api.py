import pytest
import requests
import time
import subprocess
import os
import signal
import sys

SERVER_URL = "http://localhost:3111"
WEBSITE_URL = "http://localhost:3112"

@pytest.fixture(scope="module", autouse=True)
def start_servers():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python = "/usr/local/bin/python3.12"
    
    server_proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--port", "3111"],
        cwd=os.path.join(project_dir, "Server"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "SQL5_BINARY": "/Users/ccc/.cache/sql5/sql5-macos-arm64"}
    )
    website_proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--port", "3112"],
        cwd=os.path.join(project_dir, "Website"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "SERVER_URL": SERVER_URL}
    )
    
    time.sleep(5)
    
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
    assert resp.status_code == 401

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