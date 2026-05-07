import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from Client.sync import SyncHandler, FolderWatcher
from Client.api import ApiClient

def test_sync_handler_init(temp_folder):
    api = ApiClient()
    handler = SyncHandler(api, temp_folder)
    assert handler.api == api
    assert handler.sync_folder == temp_folder
    assert isinstance(handler.file_hashes, dict)

def test_sync_handler_should_sync_valid_file(temp_folder):
    api = ApiClient()
    handler = SyncHandler(api, temp_folder)
    test_file = os.path.join(temp_folder, "test.txt")
    with open(test_file, "w") as f:
        f.write("content")
    assert handler._should_sync(test_file) == True

def test_sync_handler_should_not_sync_hidden_file(temp_folder):
    api = ApiClient()
    handler = SyncHandler(api, temp_folder)
    hidden_file = os.path.join(temp_folder, ".hidden")
    with open(hidden_file, "w") as f:
        f.write("content")
    assert handler._should_sync(hidden_file) == False

def test_sync_handler_get_file_hash(temp_folder):
    api = ApiClient()
    handler = SyncHandler(api, temp_folder)
    test_file = os.path.join(temp_folder, "test.txt")
    with open(test_file, "w") as f:
        f.write("Hello, World!")
    hash1 = handler._get_file_hash(test_file)
    hash2 = handler._get_file_hash(test_file)
    assert hash1 == hash2
    assert len(hash1) == 32

def test_sync_handler_get_file_hash_nonexistent():
    api = ApiClient()
    handler = SyncHandler(api, "/nonexistent")
    hash_val = handler._get_file_hash("/nonexistent/file.txt")
    assert hash_val == ""

def test_folder_watcher_init(temp_folder):
    api = ApiClient()
    watcher = FolderWatcher(api, temp_folder)
    assert watcher.api == api
    assert watcher.sync_folder == temp_folder
    assert watcher.observer is None