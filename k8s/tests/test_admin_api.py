import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"
DEFAULT_USER = os.getenv("DEFAULT_USER", "ccc")

from database_sqlite import init_db
import admin
init_db()

import auth
ADMIN_USER_ID = None
for r in admin.get_all_users(1, 10000)["users"]:
    if r["username"] == "ccc":
        ADMIN_USER_ID = r["id"]
        break

if ADMIN_USER_ID is None:
    try:
        uid = auth.create_user("ccc", "cccpass", "ccc@test.com")
        admin.update_user(uid, is_admin=1)
        ADMIN_USER_ID = uid
    except:
        pass

if ADMIN_USER_ID is None:
    ADMIN_USER_ID = 1

from fastapi.testclient import TestClient
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
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "running_containers" in data


class TestAdminUsersAPI:
    def test_admin_users_list(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data

    def test_admin_users_search(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/users?search=ccc", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_users_pagination(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/users?page=2", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2

    def test_admin_user_detail(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/users/1", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data

    def test_admin_user_detail_invalid(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/users/999999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_admin_update_user(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.put("/api/admin/users/1", headers={"Authorization": f"Bearer {token}"}, json={"quota_gb": 20, "is_active": 1, "is_admin": 1})
        assert resp.status_code == 200

    def test_admin_delete_invalid_user(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.delete("/api/admin/users/999999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_admin_reset_password(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/admin/users/1/reset-password", headers={"Authorization": f"Bearer {token}"}, json={"password": "newpass123"})
        assert resp.status_code == 200

    def test_admin_reset_password_short(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/admin/users/1/reset-password", headers={"Authorization": f"Bearer {token}"}, json={"password": "123"})
        assert resp.status_code == 400


class TestAdminContainersAPI:
    def test_admin_containers_list(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/containers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_admin_restart_nonexistent_container(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/admin/containers/nonexistent_user_xyz_123/restart", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    def test_admin_delete_container(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.delete("/api/admin/containers/nonexistent_user_xyz_123", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_container_logs(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/admin/containers/ccc/logs?lines=10", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "logs" in resp.json()


class TestAdminPages:
    def test_admin_dashboard_page(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_users_page(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_containers_page(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/admin/containers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
