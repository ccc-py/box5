import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "Server"))

from auth import get_password_hash, verify_password, create_access_token, verify_token

def test_password_hash():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert len(hashed) == 64

def test_verify_password_correct():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) == True

def test_verify_password_incorrect():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password("wrongpassword", hashed) == False

def test_create_access_token():
    data = {"sub": "testuser"}
    token = create_access_token(data)
    assert len(token) > 20
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"

def test_verify_token_valid():
    data = {"sub": "testuser"}
    token = create_access_token(data)
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"

def test_verify_token_invalid():
    assert verify_token("invalid.token") is None
    assert verify_token("no_dot_here") is None
    assert verify_token("") is None