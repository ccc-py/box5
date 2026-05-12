import pytest
import sys
import os
import tempfile
import hashlib
import time
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSimpleSyncImports:
    def test_can_import_simple_sync(self):
        import simple_sync
        assert hasattr(simple_sync, 'SimpleApiClient')
        assert hasattr(simple_sync, 'SimpleSyncHandler')
        assert hasattr(simple_sync, 'run_simple_sync')
        assert hasattr(simple_sync, 'main')


class TestSimpleApiClient:
    def test_client_init(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000", "key123")
        assert client.base_url == "http://localhost:8000"
        assert client.simple_key == "key123"
        assert client.token is None

    def test_client_init_no_key(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
        assert client.simple_key == ""

    def test_client_strips_trailing_slash(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_file_hash(self, tmp_path):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        h = client.get_file_hash(str(test_file))
        expected = hashlib.md5(b"hello world").hexdigest()
        assert h == expected

    def test_file_hash_nonexistent(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        h = client.get_file_hash("/nonexistent/file.txt")
        assert h == ""

    def test_headers_no_token(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        h = client._headers()
        assert h == {}

    def test_headers_with_token(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        client.token = "abc123"
        h = client._headers()
        assert h["Authorization"] == "Bearer abc123"

    def test_headers_with_simple_key(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000", "mykey")
        h = client._headers()
        assert h["X-Simple-Key"] == "mykey"

    def test_headers_with_token_and_key(self):
        from simple_sync import SimpleApiClient
        client = SimpleApiClient("http://localhost:8000", "mykey")
        client.token = "abc123"
        h = client._headers()
        assert h["Authorization"] == "Bearer abc123"
        assert h["X-Simple-Key"] == "mykey"


class TestSimpleSyncHandler:
    def test_should_sync_regular_file(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        test_file = tmp_path / "file.txt"
        test_file.write_text("hello")
        assert handler._should_sync(str(test_file)) == True

    def test_should_sync_hidden_file(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        hidden_file = tmp_path / ".hidden"
        hidden_file.write_text("secret")
        assert handler._should_sync(str(hidden_file)) == False

    def test_should_sync_node_modules(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        nm_file = tmp_path / "node_modules" / "package" / "index.js"
        nm_file.parent.mkdir(parents=True)
        nm_file.write_text("module.exports={}")
        assert handler._should_sync(str(nm_file)) == False

    def test_should_sync_pycache(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        pc_file = tmp_path / "__pycache__" / "test.pyc"
        pc_file.parent.mkdir()
        pc_file.write_bytes(b" bytecode")
        assert handler._should_sync(str(pc_file)) == False

    def test_should_sync_directory(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        assert handler._should_sync(str(tmp_path)) == False

    def test_file_hash(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")
        h = handler._file_hash(str(test_file))
        expected = hashlib.md5(b"test content").hexdigest()
        assert h == expected

    def test_file_hash_nonexistent(self):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, "/tmp/nonexistent", "")
        h = handler._file_hash("/tmp/nonexistent/file.txt")
        assert h == ""

    def test_remote_folder_set(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "backup")
        assert handler.remote_folder == "backup"

    def test_remote_files_dict(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        handler._remote_files[1] = "file.txt"
        handler._remote_files[2] = "docs/readme.md"
        assert handler._remote_files[1] == "file.txt"
        assert handler._remote_files[2] == "docs/readme.md"

    def test_local_hashes_initially_empty(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        assert handler.local_hashes == {}

    def test_sync_folder_abspath(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        rel = str(tmp_path)
        handler = SimpleSyncHandler(client, rel, "")
        assert os.path.isabs(handler.sync_folder)
        assert os.path.normpath(handler.sync_folder) == os.path.normpath(os.path.abspath(rel))

    def test_remote_folder_default_empty(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "")
        assert handler.remote_folder == ""

    def test_remote_folder_set(self, tmp_path):
        from simple_sync import SimpleSyncHandler, SimpleApiClient
        client = SimpleApiClient("http://localhost:8000")
        handler = SimpleSyncHandler(client, str(tmp_path), "backup")
        assert handler.remote_folder == "backup"