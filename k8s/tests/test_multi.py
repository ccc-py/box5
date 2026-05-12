import pytest
import sys
import os
import tempfile
import hashlib
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMultiModule:
    def test_get_mode_default(self, monkeypatch):
        monkeypatch.delenv("BOX5_MODE", raising=False)
        from multi import get_mode
        assert get_mode() == "docker"

    def test_get_mode_simple(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "simple")
        from multi import get_mode
        assert get_mode() == "simple"

    def test_get_mode_multi(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "multi")
        from multi import get_mode
        assert get_mode() == "multi"

    def test_get_mode_docker(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "docker")
        from multi import get_mode
        assert get_mode() == "docker"

    def test_get_root_default(self, monkeypatch):
        monkeypatch.delenv("BOX5_ROOT", raising=False)
        from multi import get_root
        assert get_root() == ""

    def test_get_root_set(self, monkeypatch):
        monkeypatch.setenv("BOX5_ROOT", "/data/box5")
        from multi import get_root
        assert get_root() == "/data/box5"

    def test_get_user_folder(self, monkeypatch):
        monkeypatch.setenv("BOX5_ROOT", "/data/box5")
        from multi import get_user_folder
        assert get_user_folder("alice") == "/data/box5/alice"

    def test_get_user_folder_no_root(self, monkeypatch):
        monkeypatch.delenv("BOX5_ROOT", raising=False)
        from multi import get_user_folder
        assert get_user_folder("alice") == ""

    def test_check_path_allowed_with_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("BOX5_ROOT", str(tmp_path))
        from multi import check_path_allowed, get_user_folder
        user_root = get_user_folder("alice")
        allowed_file = os.path.join(user_root, "file.txt")
        disallowed_file = "/etc/passwd"
        assert check_path_allowed(allowed_file, "alice") == True
        assert check_path_allowed(disallowed_file, "alice") == False

    def test_check_path_allowed_no_root(self, monkeypatch):
        monkeypatch.delenv("BOX5_ROOT", raising=False)
        from multi import check_path_allowed
        assert check_path_allowed("/any/path", "alice") == True

    def test_resolve_user_path_with_root(self, monkeypatch):
        monkeypatch.setenv("BOX5_ROOT", "/data/box5")
        from multi import resolve_user_path
        result = resolve_user_path("sync/file.txt", "alice")
        assert result == "/data/box5/alice/sync/file.txt"

    def test_resolve_user_path_no_root(self, monkeypatch):
        monkeypatch.delenv("BOX5_ROOT", raising=False)
        from multi import resolve_user_path
        result = resolve_user_path("sync/file.txt", "alice")
        assert result == "sync/file.txt"

    def test_is_public_path(self):
        from multi import is_public_path
        assert is_public_path("public/file.txt") == True
        assert is_public_path("public/sub/file.txt") == True
        assert is_public_path("sync/file.txt") == False
        assert is_public_path("") == False
        assert is_public_path("public") == True
        assert is_public_path("notpublic/file.txt") == False

    def test_strip_public_prefix(self):
        from multi import strip_public_prefix
        assert strip_public_prefix("public/file.txt") == "file.txt"
        assert strip_public_prefix("public/sub/file.txt") == "sub/file.txt"
        assert strip_public_prefix("sync/file.txt") == "sync/file.txt"
        assert strip_public_prefix("public") == ""

    def test_init_simple_mode(self, monkeypatch, capsys):
        monkeypatch.setenv("BOX5_MODE", "simple")
        monkeypatch.setenv("BOX5_ROOT", "/tmp/test_box5")
        from multi import init_simple_mode
        init_simple_mode()
        assert os.path.exists("/tmp/test_box5")

    def test_init_multi_mode(self, monkeypatch, capsys):
        monkeypatch.setenv("BOX5_MODE", "multi")
        monkeypatch.setenv("BOX5_ROOT", "/tmp/test_box5_multi")
        from multi import init_multi_mode
        init_multi_mode()
        assert os.path.exists("/tmp/test_box5_multi")

    def test_mode_variable(self, monkeypatch):
        monkeypatch.setenv("BOX5_MODE", "simple")
        import multi as m
        m.MODE = m.get_mode()
        assert m.MODE == "simple"

    def test_root_variable(self, monkeypatch):
        monkeypatch.setenv("BOX5_ROOT", "/custom/root")
        import multi as m
        m.ROOT = m.get_root()
        assert m.ROOT == "/custom/root"

    def test_simple_key_env(self, monkeypatch):
        monkeypatch.setenv("BOX5_SIMPLE_KEY", "secret123")
        import multi as m
        m.SIMPLE_KEY = os.getenv("BOX5_SIMPLE_KEY", "")
        assert m.SIMPLE_KEY == "secret123"