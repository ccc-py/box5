import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import docker
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

def setup_test_user_dir(username):
    user_dir = os.path.join(TEST_UPLOAD_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def cleanup_test_user_dir(username):
    user_dir = os.path.join(TEST_UPLOAD_DIR, username)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)


class TestContainerManagementFunctions:

    def test_get_container_name(self):
        from main import get_container_name
        assert get_container_name("testuser") == "box5-testuser"
        assert get_container_name("john") == "box5-john"

    @patch('main.get_client')
    def test_get_user_port(self, mock_get_client, tmp_path):
        from main import get_user_port
        import main as main_module
        original_upload = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = str(tmp_path)
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.ports.get.return_value = None
        mock_client.containers.get.side_effect = docker.errors.NotFound("test")
        mock_get_client.return_value = mock_client

        port = get_user_port("testuser")
        assert 20000 <= port <= 30000
        assert isinstance(port, int)
        port2 = get_user_port("testuser")
        assert port == port2
        main_module.UPLOAD_DIR = original_upload

    @patch('main.get_client')
    def test_create_user_container(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.ports = {'3111/tcp': [{'HostPort': '52000'}], '22/tcp': [{'HostPort': '22042'}]}
        mock_container.exec_run = MagicMock(exit_code=0, output=b"")
        mock_container.reload = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import create_user_container
        import os
        user_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'testuser')
        os.makedirs(user_dir, exist_ok=True)
        try:
            result = create_user_container("testuser", "password123")
            assert result is True
            mock_client.containers.run.assert_called_once()
            call_kwargs = mock_client.containers.run.call_args[1]
            assert call_kwargs['name'] == 'box5-testuser'
            assert call_kwargs['detach'] is True
        finally:
            import shutil
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)

    @patch('main.get_client')
    def test_create_user_container_exception(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.containers.run.side_effect = Exception("Docker error")
        mock_get_client.return_value = mock_client

        from main import create_user_container
        result = create_user_container("testuser", "password123")

        assert result is False

    @patch('main.get_client')
    def test_stop_user_container(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import stop_user_container
        result = stop_user_container("testuser")

        assert result is True
        mock_container.stop.assert_called_once_with(timeout=5)

    @patch('main.get_client')
    def test_stop_user_container_not_found(self, mock_get_client):
        import docker
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_get_client.return_value = mock_client

        from main import stop_user_container
        result = stop_user_container("testuser")

        assert result is True

    @patch('main.get_client')
    def test_delete_user_container(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import delete_user_container
        result = delete_user_container("testuser")

        assert result is True
        mock_container.remove.assert_called_once_with(force=True)

    @patch('main.get_client')
    def test_delete_user_container_not_found(self, mock_get_client):
        import docker
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_get_client.return_value = mock_client

        from main import delete_user_container
        result = delete_user_container("testuser")

        assert result is True

    def test_get_user_server_url(self):
        from main import get_user_server_url
        url = get_user_server_url("testuser")
        assert url.startswith("http://localhost:")
        assert "/api" not in url

    def test_get_user_api(self):
        from main import get_user_api
        api = get_user_api("testuser")
        assert "/api" in api

    @patch('main.get_client')
    def test_get_user_port_consistency(self, mock_get_client):
        from main import get_user_port
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.ports.get.return_value = None
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        port1 = get_user_port("user1")
        port2 = get_user_port("user1")
        assert port1 == port2
        port3 = get_user_port("user2")
        assert port3 != port1


class TestContainerStatus:

    @patch('main.get_client')
    def test_check_container_status_running(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import check_container_status
        result = check_container_status("testuser")

        assert result == "running"

    @patch('main.get_client')
    def test_check_container_status_exited(self, mock_get_client):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import check_container_status
        result = check_container_status("testuser")

        assert result == "exited"

    @patch('main.get_client')
    def test_check_container_status_not_found(self, mock_get_client):
        import docker
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
        mock_get_client.return_value = mock_client

        from main import check_container_status
        result = check_container_status("testuser")

        assert result == "not_found"

    @patch('main.get_client')
    def test_check_container_status_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("Error")
        mock_get_client.return_value = mock_client

        from main import check_container_status
        result = check_container_status("testuser")

        assert result == "error"


class TestDirectoryCreation:

    @patch('main.get_client')
    def test_create_container_creates_directories(self, mock_get_client):
        import os
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.ports = {'3111/tcp': [{'HostPort': '52001'}]}
        mock_container.reload = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_get_client.return_value = mock_client

        from main import create_user_container
        user_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'newuser')
        os.makedirs(user_dir, exist_ok=True)
        try:
            result = create_user_container("newuser", "password")
            assert result is True
        finally:
            import shutil
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)


class TestLazyClientInitialization:

    def test_get_client_returns_same_instance(self):
        with patch('main.docker.from_env') as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client

            from main import get_client
            client1 = get_client()
            client2 = get_client()

            assert client1 is client2


class TestEnvironmentVariables:

    def test_default_server_port(self):
        from main import SERVER_PORT
        assert SERVER_PORT == 3111

    def test_default_container_image(self):
        from main import CONTAINER_IMAGE
        assert CONTAINER_IMAGE == "box5-server:latest"

    def test_base_host_default(self, monkeypatch):
        monkeypatch.delenv("BOX5_HOST", raising=False)
        from main import BASE_HOST
        assert BASE_HOST == "localhost"


class TestSSHFunctions:

    def test_ssh_port_constants(self):
        from main import SSH_PORT, BASE_SSH_PORT
        assert SSH_PORT == 22
        assert BASE_SSH_PORT == 22000

    @patch('main.get_client')
    def test_get_ssh_port_from_file(self, mock_get_client, tmp_path):
        from main import get_ssh_port
        user_dir = tmp_path / "testuser"
        user_dir.mkdir()
        ssh_file = user_dir / ".ssh_port"
        ssh_file.write_text("22042")
        import main as main_module
        original_upload = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = str(tmp_path)
        try:
            port = get_ssh_port("testuser")
            assert port == 22042
        finally:
            main_module.UPLOAD_DIR = original_upload

    @patch('main.get_client')
    def test_get_ssh_port_fallback_hash(self, mock_get_client, tmp_path):
        from main import get_ssh_port
        import main as main_module
        original_upload = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = str(tmp_path)
        try:
            port = get_ssh_port("alice")
            assert 22000 <= port <= 32000
            assert isinstance(port, int)
        finally:
            main_module.UPLOAD_DIR = original_upload

    @patch('main.get_client')
    def test_get_ssh_port_consistency(self, mock_get_client, tmp_path):
        from main import get_ssh_port
        import main as main_module
        original_upload = main_module.UPLOAD_DIR
        main_module.UPLOAD_DIR = str(tmp_path)
        try:
            p1 = get_ssh_port("bob")
            p2 = get_ssh_port("bob")
            assert p1 == p2
        finally:
            main_module.UPLOAD_DIR = original_upload

    def test_create_user_in_container_success(self):
        from main import create_user_in_container
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = [
            MagicMock(exit_code=0, output=b""),     # useradd
            MagicMock(exit_code=0, output=b""),     # chpasswd
            MagicMock(exit_code=0, output=b"sshuser:$6$xxx:20585:0:99999:7:::"),  # shadow check - valid hash
        ]
        result = create_user_in_container(mock_container, "sshuser", "pass123")
        assert result is True
        assert mock_container.exec_run.call_count == 3

    def test_create_user_in_container_chpasswd_fails(self):
        from main import create_user_in_container
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = [
            MagicMock(exit_code=0, output=b""),
            MagicMock(exit_code=1, output=b"error"),
        ]
        result = create_user_in_container(mock_container, "sshuser", "pass123")
        assert result is False

    def test_create_user_in_container_useradd_fails(self):
        from main import create_user_in_container
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = [
            MagicMock(exit_code=1, output=b"user exists"),
            MagicMock(exit_code=0, output=b""),
            MagicMock(exit_code=0, output=b"sshuser:$6$xxx:20585:0:99999:7:::"),
        ]
        result = create_user_in_container(mock_container, "sshuser", "pass123")
        assert result is True


class TestSSHAPI:

    def test_get_ssh_info(self):
        with patch('main.get_ssh_port') as mock_port, \
             patch('main.BASE_HOST', 'testhost'):
            mock_port.return_value = 22042
            from main import app
            client = app.app if hasattr(app, 'app') else app
            from fastapi.testclient import TestClient
            with TestClient(app) as tc:
                resp = tc.get("/api/ssh/alice")
                assert resp.status_code == 200
                data = resp.json()
                assert data["host"] == "testhost"
                assert data["port"] == 22042
                assert data["username"] == "alice"
                assert "ssh alice@testhost -p 22042" in data["command"]