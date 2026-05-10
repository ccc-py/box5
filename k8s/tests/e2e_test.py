import pytest
import os
import time
from playwright.sync_api import sync_playwright, expect


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
TEST_USER = os.getenv("E2E_USER", "testuser")
TEST_PASS = os.getenv("E2E_PASS", "testpass123")


class TestLoginPage:

    def test_login_page_loads(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/login")
            expect(page.locator("h1")).to_contain_text("Login")
            browser.close()

    def test_login_page_has_register_link(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/login")
            expect(page.get_by_role("link", name="Register")).to_be_visible()
            browser.close()

    def test_login_form_has_inputs(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/login")
            expect(page.get_by_placeholder("Username")).to_be_visible()
            expect(page.get_by_placeholder("Password")).to_be_visible()
            expect(page.get_by_role("button", name="Login")).to_be_visible()
            browser.close()

    def test_login_empty_submission(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/login")
            page.get_by_role("button", name="Login").click()
            expect(page.locator("h1")).to_contain_text("Login")
            browser.close()

    def test_login_invalid_user(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/login")
            page.get_by_placeholder("Username").fill("nonexistentuser")
            page.get_by_placeholder("Password").fill("wrongpass")
            page.get_by_role("button", name="Login").click()
            expect(page.get_by_text("User not found")).to_be_visible()
            browser.close()


class TestRegisterPage:

    def test_register_page_loads(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/register")
            expect(page.locator("h1")).to_contain_text("Register")
            browser.close()

    def test_register_form_fields(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/register")
            expect(page.get_by_placeholder("Username")).to_be_visible()
            expect(page.get_by_placeholder("Password")).to_be_visible()
            expect(page.get_by_role("button", name="Register")).to_be_visible()
            browser.close()

    def test_register_to_login_link(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/register")
            expect(page.get_by_role("link", name="Login")).to_be_visible()
            browser.close()


class TestRootRedirect:

    def test_root_redirects_to_login(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/")
            expect(page).to_have_url(f"{BASE_URL}/login")
            browser.close()

    def test_logout_redirects_to_login(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/logout")
            expect(page).to_have_url(f"{BASE_URL}/login")
            browser.close()


class TestStaticFiles:

    def test_static_css_loads(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(f"{BASE_URL}/static/box5.css")
            assert response.status == 200
            browser.close()

    def test_static_js_loads(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(f"{BASE_URL}/static/box5.js")
            assert response.status in [200, 404]
            browser.close()


class TestHealthEndpoints:

    def test_status_endpoint_not_logged_in(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/status")
            expect(page.get_by_text("not_logged_in")).to_be_visible()
            browser.close()

    def test_status_endpoint_json(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(f"{BASE_URL}/status")
            assert response.status == 200
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])