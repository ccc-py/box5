import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import docker


_original_docker = None


@pytest.fixture(scope="session", autouse=True)
def mock_docker_session():
    global _original_docker
    _original_docker = docker.from_env
    docker.from_env = MagicMock(return_value=MagicMock())
    yield
    if _original_docker is not None:
        docker.from_env = _original_docker


@pytest.fixture(autouse=True)
def reset_main_client():
    import main
    main._client = None
    yield


@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_docker():
    return docker.from_env()


@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        yield (mock_get, mock_post)