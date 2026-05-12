import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


class TestMultiModeFileAPIs:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, tmp_path):
        self.storage = tmp_path / "storage"
        self.storage.mkdir()
        monkeypatch.setenv("BOX5_MODE", "multi")
        monkeypatch.setenv("BOX5_ROOT", str(self.storage))
        monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

        from database_sqlite import init_db
        init_db()

        if "main" in sys.modules:
            del sys.modules["main"]
        if "multi" in sys.modules:
            del sys.modules["multi"]

        import multi as m
        m.MODE = "multi"
        m.ROOT = str(self.storage)
        import main
        self.client = TestClient(main.app)
        self.user_dir = self.storage / "alice"
        self.user_dir.mkdir()

    def test_list_files_anon(self):
        r = self.client.get("/api/files")
        assert r.status_code == 401

    def test_list_files_auth(self, monkeypatch):
        import auth
        user_id = auth.create_user("alice", "pass123", "")
        token = auth.create_access_token(user_id, "alice")
        r = self.client.get("/api/files", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_list_files_creates_sync_folder(self):
        import auth
        user_id = auth.create_user("bob", "pass123", "")
        token = auth.create_access_token(user_id, "bob")
        sync_dir = self.storage / "bob" / "sync"
        sync_dir.mkdir(parents=True, exist_ok=True)
        (sync_dir / "notes.txt").write_text("hello")
        r = self.client.get("/api/files", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert any(f["filename"] == "notes.txt" for f in data["files"])

    def test_upload_requires_auth(self):
        r = self.client.post("/api/files/upload", files={"file": ("test.txt", b"hello")})
        assert r.status_code == 401

    def test_upload_creates_file(self, tmp_path):
        import auth
        user_id = auth.create_user("carol", "pass123", "")
        token = auth.create_access_token(user_id, "carol")

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        with open(f, "rb") as fh:
            r = self.client.post("/api/files/upload",
                files={"file": ("test.txt", fh.read())},
                data={"folder": ""},
                headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["files"]) == 1
        uploaded_path = self.storage / "carol" / "sync" / "test.txt"
        assert uploaded_path.exists()
        assert uploaded_path.read_text() == "hello world"

    def test_upload_to_subfolder(self, tmp_path):
        import auth
        user_id = auth.create_user("dave", "pass123", "")
        token = auth.create_access_token(user_id, "dave")

        f = tmp_path / "data.csv"
        f.write_text("col1,col2")
        with open(f, "rb") as fh:
            r = self.client.post("/api/files/upload",
                files={"file": ("data.csv", fh.read())},
                data={"folder": "docs"},
                headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        sub_path = self.storage / "dave" / "sync" / "docs" / "data.csv"
        assert sub_path.exists()

    def test_public_files_endpoint(self):
        pub_dir = self.storage / "public"
        pub_dir.mkdir(exist_ok=True)
        (pub_dir / "readme.txt").write_text("public content")
        r = self.client.get("/api/public/files")
        assert r.status_code == 200
        files = r.json()
        assert any(f["filename"] == "readme.txt" for f in files)

    def test_public_files_not_in_docker_mode(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "docker")
        if "main" in sys.modules:
            del sys.modules["main"]
        import multi as m
        m.MODE = "docker"
        import main
        client = TestClient(main.app)
        r = client.get("/api/public/files")
        assert r.status_code == 403

    def test_delete_file_auth(self):
        r = self.client.delete("/api/files/999")
        assert r.status_code == 401

    def test_delete_nonexistent(self):
        import auth
        user_id = auth.create_user("eve", "pass123", "")
        token = auth.create_access_token(user_id, "eve")
        r = self.client.delete("/api/files/99999",
            headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404


class TestSimpleModeFileAPIs:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, tmp_path):
        self.storage = tmp_path / "storage"
        self.storage.mkdir()
        monkeypatch.setenv("BOX5_MODE", "simple")
        monkeypatch.setenv("BOX5_ROOT", str(self.storage))
        monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))

        from database_sqlite import init_db
        init_db()

        for m in ["main", "multi"]:
            if m in sys.modules:
                del sys.modules[m]

        import multi as m
        m.MODE = "simple"
        m.ROOT = str(self.storage)
        import main
        self.client = TestClient(main.app)

    def test_simple_login(self):
        r = self.client.post("/api/simple/login")
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_simple_login_with_key(self, monkeypatch):
        monkeypatch.setenv("BOX5_SIMPLE_KEY", "mysecretkey")
        for m in ["main", "multi"]:
            if m in sys.modules:
                del sys.modules[m]
        import multi as m
        m.MODE = "simple"
        m.ROOT = str(self.storage)
        m.SIMPLE_KEY = "mysecretkey"
        import main
        client = TestClient(main.app)

        r = client.post("/api/simple/login", headers={"X-Simple-Key": "mysecretkey"})
        assert r.status_code == 200

        r = client.post("/api/simple/login", headers={"X-Simple-Key": "wrong"})
        assert r.status_code == 401

    def test_simple_mode_file_anon_upload(self, tmp_path):
        f = tmp_path / "anon.txt"
        f.write_text("anonymous upload")
        with open(f, "rb") as fh:
            r = self.client.post("/api/files/upload",
                files={"file": ("anon.txt", fh.read())})
        assert r.status_code == 200
        anon_path = self.storage / "simple" / "anon.txt"
        assert anon_path.exists()

    def test_simple_mode_file_list_anon(self):
        (self.storage / "sync").mkdir(exist_ok=True)
        r = self.client.get("/api/files")
        assert r.status_code == 200

    def test_simple_login_not_in_multi_mode(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "multi")
        for m in ["main", "multi"]:
            if m in sys.modules:
                del sys.modules[m]
        import multi as m
        m.MODE = "multi"
        m.ROOT = str(self.storage)
        import main
        client = TestClient(main.app)
        r = client.post("/api/simple/login")
        assert r.status_code == 403