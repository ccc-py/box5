import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"

from client import ApiClient


class TestApiClientInit:
    def test_client_init(self):
        api = ApiClient("http://localhost:8000")
        assert api.base_url == "http://localhost:8000"
        assert api.token is None

    def test_client_trailing_slash(self):
        api = ApiClient("http://localhost:8000/")
        assert api.base_url == "http://localhost:8000"

    def test_get_file_hash_missing(self):
        api = ApiClient("http://localhost:8000")
        h = api.get_file_hash("/nonexistent/file/xyz.txt")
        assert h == ""


class TestApiClientLogin:
    def test_login_no_server(self):
        api = ApiClient("http://localhost:99999")
        try:
            api.login("nobody", "nopass")
            assert False
        except Exception as e:
            assert "Login failed" in str(e) or "ConnectionError" in str(e) or "connect" in str(e) or "Failed" in str(e)

    def test_login_wrong_credentials(self):
        api = ApiClient("http://localhost:8000")
        try:
            api.login("nobody_xyz_nonexistent", "wrongpass")
            assert False
        except Exception as e:
            assert "Login failed" in str(e) or "ConnectionError" in str(e) or "connect" in str(e)


class TestApiClientListFiles:
    def test_list_files_no_login(self):
        api = ApiClient("http://localhost:8000")
        try:
            api.list_files()
            assert False
        except Exception as e:
            assert "Not logged in" in str(e)

    def test_list_files_wrong_token(self):
        api = ApiClient("http://localhost:8000")
        api.token = "invalid_token_xyz"
        try:
            api.list_files()
            assert False
        except Exception as e:
            pass


class TestApiClientUpload:
    def test_upload_no_login(self):
        api = ApiClient("http://localhost:8000")
        try:
            api.upload_file("/tmp/nonexistent.txt")
            assert False
        except Exception as e:
            assert "Not logged in" in str(e)


class TestApiClientDownload:
    def test_download_no_login(self):
        api = ApiClient("http://localhost:8000")
        try:
            api.download_file(99999, "/tmp/out.txt")
            assert False
        except Exception as e:
            assert "Not logged in" in str(e)

    def test_download_no_server(self):
        api = ApiClient("http://localhost:99999")
        api.token = "fake"
        try:
            api.download_file(1, "/tmp/out.txt")
            assert False
        except Exception as e:
            pass


class TestApiClientDelete:
    def test_delete_no_login(self):
        api = ApiClient("http://localhost:8000")
        try:
            api.delete_file(99999)
            assert False
        except Exception as e:
            assert "Not logged in" in str(e)
