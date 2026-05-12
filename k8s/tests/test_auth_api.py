import sys
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

if "/Users/Shared/ccc/project/box5/k8s" not in sys.path:
    sys.path.insert(0, "/Users/Shared/ccc/project/box5/k8s")

TEST_DB_DIR = tempfile.mkdtemp()
TEST_DB = os.path.join(TEST_DB_DIR, "test_auth_api.db")
os.environ["DB_PATH"] = TEST_DB


@pytest.fixture(autouse=True)
def setup_db():
    from database_sqlite import init_db, get_db
    init_db()
    db = get_db()
    db.execute("DELETE FROM users")
    db.execute("DELETE FROM user_profiles")
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM login_history")
    db.commit()
    db.close()
    yield


class TestAuthRegisterAPI:

    def test_register_success(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/auth/register", json={"username": "alice", "password": "password123", "email": "alice@example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "User registered"
        assert data["user_id"] is not None

    def test_register_duplicate(self):
        from main import app
        from auth import create_user
        create_user("bob", "pass123")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/auth/register", json={"username": "bob", "password": "pass456"})
        assert resp.status_code == 400

    def test_register_short_password(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/auth/register", json={"username": "alice2", "password": "123"})
        assert resp.status_code == 400
        assert "6 characters" in resp.json()["error"]

    def test_register_short_username(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/auth/register", json={"username": "ab", "password": "password123"})
        assert resp.status_code == 400
        assert "3 characters" in resp.json()["error"]


class TestAuthMeAPI:

    def test_me_with_token(self):
        from main import app
        from auth import create_user, create_access_token
        user_id = create_user("carol", "pass123", "carol@example.com")
        token = create_access_token(user_id, "carol")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "carol"
        assert data["email"] == "carol@example.com"

    def test_me_no_token(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestAuthLoginHistoryAPI:

    def test_login_history(self):
        from main import app
        from auth import create_user, create_access_token, record_login
        user_id = create_user("dave", "pass123")
        record_login(user_id, "192.168.1.1", "TestBrowser")
        token = create_access_token(user_id, "dave")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/auth/login-history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["ip"] == "192.168.1.1"


class TestAPIKeysAPI:

    def test_create_and_list_keys(self):
        from main import app
        from auth import create_user, create_access_token
        user_id = create_user("eve", "pass123")
        token = create_access_token(user_id, "eve")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/keys", headers={"Authorization": f"Bearer {token}"}, json={"name": "Test Key", "permissions": "read"})
        assert resp.status_code == 200
        data = resp.json()
        assert "key" in data
        assert data["key"].startswith("box5_sk_")
        assert data["name"] == "Test Key"

        resp = client.get("/api/keys", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 1

    def test_revoke_key(self):
        from main import app
        from auth import create_user, create_access_token
        user_id = create_user("frank", "pass123")
        token = create_access_token(user_id, "frank")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/keys", headers={"Authorization": f"Bearer {token}"}, json={"name": "Revoke Me"})
        key_id = resp.json()["id"]
        resp = client.delete(f"/api/keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Key revoked"


class TestVerifyEmailPage:

    def test_verify_email_no_token(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/verify-email")
        assert resp.status_code == 200

    def test_verify_email_invalid_token(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/verify-email?token=nonexistent")
        assert resp.status_code == 200
        assert "Invalid token" in resp.text


class TestForgotPasswordPage:

    def test_forgot_password_page(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/forgot-password")
        assert resp.status_code == 200
        assert "Reset Password" in resp.text


class TestResetPasswordPage:

    def test_reset_password_expired(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/reset-password?token=invalidtoken")
        assert resp.status_code == 200

    def test_reset_password_no_token(self):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/reset-password")
        assert resp.status_code == 200