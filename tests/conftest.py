import pytest
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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