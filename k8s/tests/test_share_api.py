import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"

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


class TestShareAPI:
    def test_create_share(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/shares", headers={"Authorization": f"Bearer {token}"}, json={
            "file_path": "/test/create_share_test.txt",
            "password": "",
            "expires_hours": 0,
            "max_downloads": 0
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "token" in data

    def test_create_share_with_password(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/shares", headers={"Authorization": f"Bearer {token}"}, json={
            "file_path": "/test/create_share_with_pass.txt",
            "password": "secret123",
            "expires_hours": 24,
            "max_downloads": 10
        })
        assert resp.status_code == 200

    def test_create_share_no_auth(self):
        client = TestClient(app)
        resp = client.post("/api/shares", json={"file_path": "/test/file.txt"})
        assert resp.status_code == 401

    def test_list_shares(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/api/shares", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_shares_no_auth(self):
        client = TestClient(app)
        resp = client.get("/api/shares")
        assert resp.status_code == 401

    def test_get_share_invalid_token(self):
        client = TestClient(app)
        resp = client.get("/api/shares/share_invalid_token_xyz")
        assert resp.status_code == 404

    def test_delete_share_no_auth(self):
        client = TestClient(app)
        resp = client.delete("/api/shares/1")
        assert resp.status_code == 401

    def test_unlock_share(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.post("/api/shares", headers={"Authorization": f"Bearer {token}"}, json={
            "file_path": "/test/unlock_test.txt",
            "password": "unlockpass"
        })
        assert resp.status_code == 200
        share_token = resp.json()["token"]

        resp2 = client.post(f"/api/shares/{share_token}/unlock", json={"password": "wrong"})
        assert resp2.status_code == 403

        resp3 = client.post(f"/api/shares/{share_token}/unlock", json={"password": "unlockpass"})
        assert resp3.status_code == 200

    def test_download_share_no_auth(self):
        client = TestClient(app)
        resp = client.get("/api/shares/share_invalid/download")
        assert resp.status_code == 404


class TestSharePages:
    def test_shares_page_no_auth(self):
        client = TestClient(app)
        resp = client.get("/shares")
        assert resp.status_code in [200, 302, 401]

    def test_shares_page_with_auth(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/shares", cookies={"token": token, "username": "ccc"})
        assert resp.status_code == 200

    def test_share_page_invalid(self):
        client = TestClient(app)
        resp = client.get("/share/share_invalid_token_xyz")
        assert resp.status_code == 404
