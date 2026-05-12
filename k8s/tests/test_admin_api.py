import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"
DEFAULT_USER = os.getenv("DEFAULT_USER", "ccc")

from database_sqlite import init_db, get_db as _get_db
import admin
import auth

init_db()

def _find_admin_user():
    for r in admin.get_all_users(1, 10000)["users"]:
        if r["username"] == "ccc":
            return r["id"]
    return None

ADMIN_USER_ID = _find_admin_user()
print("AAA ADMIN_USER_ID after search:", ADMIN_USER_ID)

if ADMIN_USER_ID:
    db = _get_db()
    db.execute("INSERT OR IGNORE INTO user_profiles (user_id, is_admin, is_active) VALUES (?, 1, 1)", (ADMIN_USER_ID,))
    db.commit()
    is_ok = db.execute("SELECT is_admin FROM user_profiles WHERE user_id = ?", (ADMIN_USER_ID,)).fetchone()
    print("AAA is_admin after insert:", is_ok["is_admin"] if is_ok else None)
    db.close()
else:
    print("AAA No ccc user found, creating...")
    try:
        uid = auth.create_user("ccc", "cccpass", "ccc@test.com")
        print("AAA create_user returned:", uid)
        if uid:
            admin.update_user(uid, is_admin=1)
            ADMIN_USER_ID = uid
            db = _get_db()
            is_ok = db.execute("SELECT is_admin FROM user_profiles WHERE user_id = ?", (uid,)).fetchone()
            print("AAA is_admin after update:", is_ok["is_admin"] if is_ok else None)
            db.close()
    except Exception as e:
        print("AAA create_user failed:", e)

print("AAA FINAL ADMIN_USER_ID:", ADMIN_USER_ID)
print("AAA is_admin:", admin.is_admin_user(ADMIN_USER_ID) if ADMIN_USER_ID else "None")

def get_admin_token():
    """Ensure admin user exists and has admin status at call time."""
    db = _get_db()
    row = db.execute("SELECT id FROM users WHERE username = ?", ("ccc",)).fetchone()
    if row:
        uid = row["id"]
    else:
        uid = auth.create_user("ccc", "cccpass", "ccc@test.com")
        admin.update_user(uid, is_admin=1)

    db.execute("INSERT OR IGNORE INTO user_profiles (user_id, is_admin, is_active) VALUES (?, 1, 1)", (uid,))
    db.execute("UPDATE user_profiles SET is_admin = 1 WHERE user_id = ?", (uid,))
    db.commit()
    db.close()

    global ADMIN_USER_ID
    ADMIN_USER_ID = uid

    token = auth.create_access_token(uid, "ccc")
    ok = admin.is_admin_user(uid)
    print(f"AAA get_admin_token: uid={uid}, is_admin={ok}")
    return token

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app


class TestAdminAuth:
    def test_admin_dashboard_no_token(self):
        client = TestClient(app)
        resp = client.get("/api/admin/dashboard")
        assert resp.status_code == 401

    def test_admin_dashboard_invalid_token(self):
        client = TestClient(app)
        resp = client.get("/api/admin/dashboard", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestAdminDashboard:
    def test_admin_dashboard(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        print("AAA response:", resp.status_code, resp.text)
        assert resp.status_code == 200


class TestAdminUsersAPI:
    def test_admin_users_list(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data

    def test_admin_users_search(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/api/admin/users?search=ccc", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_users_pagination(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/api/admin/users?page=2", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2

    def test_admin_user_detail(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get(f"/api/admin/users/{ADMIN_USER_ID}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data

    def test_admin_user_detail_invalid(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/api/admin/users/999999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_admin_update_user(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.put(f"/api/admin/users/{ADMIN_USER_ID}", headers={"Authorization": f"Bearer {token}"}, json={"quota_gb": 20, "is_active": 1, "is_admin": 1})
        assert resp.status_code == 200

    def test_admin_delete_invalid_user(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.delete("/api/admin/users/999999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_admin_reset_password(self):
        client = TestClient(app)
        token = get_admin_token()
        with patch('main.get_client') as mock_gc:
            mock_client = MagicMock()
            mock_gc.return_value = mock_client
            resp = client.post(f"/api/admin/users/{ADMIN_USER_ID}/reset-password", headers={"Authorization": f"Bearer {token}"}, json={"password": "newpass123"})
            assert resp.status_code == 200

    def test_admin_reset_password_short(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.post(f"/api/admin/users/{ADMIN_USER_ID}/reset-password", headers={"Authorization": f"Bearer {token}"}, json={"password": "123"})
        assert resp.status_code == 400


class TestAdminContainersAPI:
    def test_admin_containers_list(self):
        client = TestClient(app)
        token = get_admin_token()
        with patch('main.get_client') as mock_gc:
            mock_client = MagicMock()
            mock_client.containers.list.return_value = []
            mock_gc.return_value = mock_client
            resp = client.get("/api/admin/containers", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

    def test_admin_restart_nonexistent_container(self):
        client = TestClient(app)
        token = get_admin_token()
        with patch('main.get_client') as mock_gc:
            mock_client = MagicMock()
            mock_client.containers.get.side_effect = Exception("not found")
            mock_gc.return_value = mock_client
            resp = client.post("/api/admin/containers/nonexistent_user_xyz_123/restart", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404

    def test_admin_delete_container(self):
        client = TestClient(app)
        token = get_admin_token()
        with patch('main.get_client') as mock_gc:
            mock_client = MagicMock()
            mock_client.containers.get.side_effect = Exception("not found")
            mock_gc.return_value = mock_client
            resp = client.delete("/api/admin/containers/nonexistent_user_xyz_123", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200

    def test_admin_container_logs(self):
        client = TestClient(app)
        token = get_admin_token()
        with patch('main.get_client') as mock_gc:
            mock_client = MagicMock()
            mock_client.containers.get.side_effect = Exception("not found")
            mock_gc.return_value = mock_client
            resp = client.get(f"/api/admin/containers/{ADMIN_USER_ID}/logs?lines=10", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert "logs" in resp.json()


class TestAdminPages:
    def test_admin_dashboard_page(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_users_page(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_containers_page(self):
        client = TestClient(app)
        token = get_admin_token()
        resp = client.get("/admin/containers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
