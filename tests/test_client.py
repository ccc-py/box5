import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "Client"))

from Client.api import ApiClient

def test_api_client_init():
    api = ApiClient()
    assert api.base_url == "http://localhost:3111"
    assert api.token is None

def test_api_client_custom_url():
    api = ApiClient("http://custom:9000")
    assert api.base_url == "http://custom:9000"

def test_api_client_has_required_methods():
    api = ApiClient()
    assert hasattr(api, "register")
    assert hasattr(api, "login")
    assert hasattr(api, "upload_file")
    assert hasattr(api, "list_files")
    assert hasattr(api, "download_file")
    assert hasattr(api, "delete_file")