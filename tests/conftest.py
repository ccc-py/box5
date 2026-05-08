import pytest
import os
import sys
import tempfile
import shutil
import time
import subprocess
import requests
import uuid
from multiprocessing import Process

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

unique_id = uuid.uuid4().hex[:8]

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = path
    yield path
    try:
        os.unlink(path)
    except:
        pass

@pytest.fixture
def temp_folder():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)

@pytest.fixture
def sample_file(temp_folder):
    filepath = os.path.join(temp_folder, "test.txt")
    with open(filepath, "w") as f:
        f.write("Hello, World!")
    return filepath

@pytest.fixture(scope="module")
def server_url():
    return "http://localhost:3111"

@pytest.fixture(scope="module")
def website_url():
    return "http://localhost:3112"

@pytest.fixture(scope="module")
def test_user():
    return {"username": f"testuser_{unique_id}", "password": "testpass123"}