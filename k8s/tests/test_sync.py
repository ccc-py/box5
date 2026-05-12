import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"

from sync_client import SyncHandler, FolderWatcher
from client import ApiClient


class TestSyncHandler:
    def test_should_sync_regular_file(self, tmp_path):
        sync_dir = str(tmp_path / "sync_test")
        os.makedirs(sync_dir, exist_ok=True)
        with open(os.path.join(sync_dir, "test.txt"), "w") as f:
            f.write("x")
        with open(os.path.join(sync_dir, "test.py"), "w") as f:
            f.write("x")
        with open(os.path.join(sync_dir, ".hidden.txt"), "w") as f:
            f.write("x")
        os.makedirs(os.path.join(sync_dir, "node_modules"), exist_ok=True)
        with open(os.path.join(sync_dir, "node_modules/foo.js"), "w") as f:
            f.write("x")
        os.makedirs(os.path.join(sync_dir, "__pycache__"), exist_ok=True)
        with open(os.path.join(sync_dir, "__pycache__/foo.py"), "w") as f:
            f.write("x")
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, sync_dir, "")
        assert handler._should_sync(os.path.join(sync_dir, "test.txt")) is True
        assert handler._should_sync(os.path.join(sync_dir, "test.py")) is True
        assert handler._should_sync(os.path.join(sync_dir, ".hidden.txt")) is False
        assert handler._should_sync(os.path.join(sync_dir, "node_modules/foo.js")) is False
        assert handler._should_sync(os.path.join(sync_dir, "__pycache__/foo.py")) is False

    def test_is_public(self, tmp_path):
        sync_dir = str(tmp_path / "sync_test")
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, sync_dir, "")
        assert handler._is_public(os.path.join(sync_dir, "public/file.txt")) is True
        assert handler._is_public(os.path.join(sync_dir, "file.txt")) is False
        assert handler._is_public(os.path.join(sync_dir, "public/sub/file.txt")) is True

    def test_get_subfolder_root(self, tmp_path):
        sync_dir = str(tmp_path / "sync_test")
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, sync_dir, "")
        assert handler._get_subfolder(os.path.join(sync_dir, "file.txt")) == ""

    def test_get_subfolder_nested(self, tmp_path):
        sync_dir = str(tmp_path / "sync_test")
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, sync_dir, "myfolder")
        assert handler._get_subfolder(os.path.join(sync_dir, "docs/readme.md")) == "myfolder/docs"

    def test_get_subfolder_public(self, tmp_path):
        sync_dir = str(tmp_path / "sync_test")
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, sync_dir, "myfolder")
        result = handler._get_subfolder(os.path.join(sync_dir, "public/image.png"))
        assert result == "myfolder" or result == "myfolder/image.png"

    def test_file_hash_missing(self):
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, "/tmp/sync_test", "")
        assert handler._file_hash("/tmp/nonexistent_xyz_file.txt") == ""

    def test_file_hash_existing(self):
        import tempfile
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, "/tmp/sync_test", "")
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("hello world")
            temp_path = f.name
        try:
            h = handler._file_hash(temp_path)
            assert h != ""
            assert len(h) == 32
        finally:
            os.unlink(temp_path)

    def test_hash_consistency(self):
        import tempfile
        api = ApiClient("http://localhost:8000")
        handler = SyncHandler(api, "/tmp/sync_test", "")
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("test content")
            temp_path = f.name
        try:
            h1 = handler._file_hash(temp_path)
            h2 = handler._file_hash(temp_path)
            assert h1 == h2
        finally:
            os.unlink(temp_path)


class TestFolderWatcher:
    def test_watcher_init(self):
        api = ApiClient("http://localhost:8000")
        watcher = FolderWatcher(api, "/tmp/sync_test", "")
        assert watcher.sync_folder == os.path.abspath("/tmp/sync_test")
        assert watcher.folder == ""
        assert watcher.observer is None

    def test_watcher_with_remote_folder(self):
        api = ApiClient("http://localhost:8000")
        watcher = FolderWatcher(api, "/tmp/sync_test", "myfiles")
        assert watcher.folder == "myfiles"
        assert watcher.handler.folder == "myfiles"

    def test_watcher_creates_directory(self, tmp_path):
        api = ApiClient("http://localhost:8000")
        sync_dir = str(tmp_path / "sync_new")
        watcher = FolderWatcher(api, sync_dir, "")
        watcher.start()
        assert os.path.exists(sync_dir)
        watcher.stop()


class TestSyncModuleImports:
    def test_imports(self):
        from sync_client import SyncHandler, FolderWatcher, run_sync
        assert SyncHandler is not None
        assert FolderWatcher is not None
        assert run_sync is not None
