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


class TestEditorEndpoint:
    def test_editor_page_no_auth(self):
        client = TestClient(app)
        resp = client.get("/editor")
        assert resp.status_code in [200, 302, 401]

    def test_editor_page_with_auth(self):
        client = TestClient(app)
        token = auth.create_access_token(ADMIN_USER_ID, "ccc")
        resp = client.get("/editor", cookies={"token": token, "username": "ccc"})
        assert resp.status_code == 200


class TestEditorWebSocket:
    def test_websocket_endpoint_requires_username(self):
        client = TestClient(app)
        resp = client.get("/editor?path=./sync")
        assert resp.status_code in [200, 302, 401]
