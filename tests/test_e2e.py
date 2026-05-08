import pytest
import time
import subprocess
import os
import sys
import uuid
import pathlib

SERVER_URL = "http://localhost:3111"
WEBSITE_URL = "http://localhost:3112"

unique_id = uuid.uuid4().hex[:8]

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
import os
os.environ['SERVER_URL'] = '{SERVER_URL}'
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
    time.sleep(2)
    website_proc = subprocess.Popen(
        [venv_python, "-c", website_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
        cwd=project_dir
    )

    time.sleep(8)

    if server_proc.poll() is not None:
        _, stderr = server_proc.communicate()
        print(f"Server failed to start: {stderr.decode()}")

    if website_proc.poll() is not None:
        _, stderr = website_proc.communicate()
        print(f"Website failed to start: {stderr.decode()}")

    yield

    server_proc.terminate()
    website_proc.terminate()
    server_proc.wait()
    website_proc.wait()

@pytest.fixture(scope="module")
def browser_page():
    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    yield page
    browser.close()
    playwright.stop()

@pytest.fixture(scope="module")
def e2e_user():
    return {"username": f"e2euser_{unique_id}", "password": "e2epass123"}

def test_website_login_page_loads(browser_page):
    browser_page.goto(f"{WEBSITE_URL}/login")
    assert browser_page.title() == "Login - box5"
    assert browser_page.locator("input[name='username']").is_visible()
    assert browser_page.locator("input[name='password']").is_visible()

def test_website_register_page_loads(browser_page):
    browser_page.goto(f"{WEBSITE_URL}/register")
    assert "Register" in browser_page.title()

def test_user_registration(browser_page, e2e_user):
    browser_page.goto(f"{WEBSITE_URL}/register")
    browser_page.fill("input[name='username']", e2e_user["username"])
    browser_page.fill("input[name='password']", e2e_user["password"])
    browser_page.click("button[type='submit']")
    browser_page.wait_for_url(f"{WEBSITE_URL}/login")
    assert "/login" in browser_page.url

def test_user_login(browser_page, e2e_user):
    browser_page.goto(f"{WEBSITE_URL}/login")
    browser_page.fill("input[name='username']", e2e_user["username"])
    browser_page.fill("input[name='password']", e2e_user["password"])
    browser_page.click("button[type='submit']")
    browser_page.wait_for_url(f"{WEBSITE_URL}/")
    assert browser_page.url == f"{WEBSITE_URL}/"

def test_user_login_invalid(browser_page):
    browser_page.goto(f"{WEBSITE_URL}/login")
    browser_page.fill("input[name='username']", "invaliduser")
    browser_page.fill("input[name='password']", "wrongpass")
    browser_page.click("button[type='submit']")
    assert "Login failed" in browser_page.content() or browser_page.url.endswith("/login")

def test_file_list_after_login(browser_page, e2e_user):
    browser_page.goto(f"{WEBSITE_URL}/login")
    browser_page.fill("input[name='username']", e2e_user["username"])
    browser_page.fill("input[name='password']", e2e_user["password"])
    browser_page.click("button[type='submit']")
    browser_page.wait_for_load_state("networkidle")
    assert "box5" in browser_page.title()

def test_logout(browser_page, e2e_user):
    browser_page.goto(f"{WEBSITE_URL}/login")
    browser_page.fill("input[name='username']", e2e_user["username"])
    browser_page.fill("input[name='password']", e2e_user["password"])
    browser_page.click("button[type='submit']")
    browser_page.wait_for_url(f"{WEBSITE_URL}/")
    browser_page.click("text=Logout")
    browser_page.wait_for_url(f"{WEBSITE_URL}/login")

def test_public_files_page(browser_page):
    browser_page.goto(f"{WEBSITE_URL}/public")
    assert "Public" in browser_page.content() or "box5" in browser_page.title()

def test_redirect_to_login(browser_page):
    browser_page.goto(f"{WEBSITE_URL}/")
    assert "/login" in browser_page.url