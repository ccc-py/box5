import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_docker():
    with patch('docker.from_env') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        yield (mock_get, mock_post)