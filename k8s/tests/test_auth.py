import sys
import os
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch

if "/Users/Shared/ccc/project/box5/k8s" not in sys.path:
    sys.path.insert(0, "/Users/Shared/ccc/project/box5/k8s")


TEST_DB_DIR = tempfile.mkdtemp()
TEST_DB = os.path.join(TEST_DB_DIR, "test_auth.db")
os.environ["DB_PATH"] = TEST_DB


class TestPasswordHashing:
    def test_hash_password_produces_hash(self):
        from auth import hash_password
        h = hash_password("testpass123")
        assert h is not None
        assert h != "testpass123"
        assert len(h) > 20

    def test_hash_password_different_each_time(self):
        from auth import hash_password
        h1 = hash_password("pass")
        h2 = hash_password("pass")
        assert h1 != h2

    def test_verify_password_correct(self):
        from auth import hash_password, verify_password
        h = hash_password("correct_password")
        assert verify_password("correct_password", h) is True

    def test_verify_password_wrong(self):
        from auth import hash_password, verify_password
        h = hash_password("correct_password")
        assert verify_password("wrong_password", h) is False


class TestTokens:
    def test_create_access_token(self):
        from auth import create_access_token, decode_token
        token = create_access_token(1, "testuser")
        assert token is not None
        assert len(token) > 20
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"

    def test_decode_invalid_token(self):
        from auth import decode_token
        payload = decode_token("invalid_token")
        assert payload is None

    def test_create_verify_token(self):
        from auth import create_verify_token
        t = create_verify_token()
        assert t is not None
        assert len(t) > 10

    def test_create_reset_token(self):
        from auth import create_reset_token
        t = create_reset_token()
        assert t is not None
        assert len(t) > 10

    def test_generate_api_key(self):
        from auth import generate_api_key
        raw, key_hash, key_prefix = generate_api_key()
        assert raw.startswith("box5_sk_")
        assert len(key_prefix) == 16
        assert len(key_hash) == 64


class TestUserCreation:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.execute("DELETE FROM api_keys")
        db.execute("DELETE FROM login_history")
        db.commit()
        db.close()

    def test_create_user_success(self):
        from auth import create_user, get_user_by_username
        user_id = create_user("alice", "password123", "alice@example.com")
        assert user_id is not None
        user = get_user_by_username("alice")
        assert user is not None
        assert user["username"] == "alice"

    def test_create_user_duplicate(self):
        from auth import create_user
        create_user("bob", "pass123", "bob@example.com")
        result = create_user("bob", "pass456", "bob2@example.com")
        assert result is None

    def test_get_user_by_id(self):
        from auth import create_user, get_user_by_id
        user_id = create_user("charlie", "pass999")
        user = get_user_by_id(user_id)
        assert user is not None
        assert user["username"] == "charlie"

    def test_get_user_by_username_not_found(self):
        from auth import get_user_by_username
        user = get_user_by_username("nonexistent")
        assert user is None


class TestPasswordUpdate:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.commit()
        db.close()

    def test_update_user_password(self):
        from auth import create_user, update_user_password, verify_password, get_user_by_username, hash_password
        user_id = create_user("dave", "oldpass")
        update_user_password(user_id, "newpass")
        user = get_user_by_username("dave")
        assert verify_password("newpass", user["password_hash"]) is True
        assert verify_password("oldpass", user["password_hash"]) is False


class TestEmailVerification:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.commit()
        db.close()

    def test_verify_user_email(self):
        from auth import create_user, verify_user_email, get_user_profile
        user_id = create_user("eve", "pass123", "eve@example.com")
        verify_user_email(user_id)
        profile = get_user_profile(user_id)
        assert profile["email_verified"] == 1


class TestPasswordReset:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.commit()
        db.close()

    def test_set_and_get_reset_token(self):
        from auth import create_user, set_reset_token, get_user_by_reset_token
        user_id = create_user("frank", "pass123", "frank@example.com")
        token = set_reset_token(user_id)
        assert token is not None
        user = get_user_by_reset_token(token)
        assert user is not None
        assert user["username"] == "frank"

    def test_clear_reset_token(self):
        from auth import create_user, set_reset_token, clear_reset_token, get_user_by_reset_token
        user_id = create_user("grace", "pass123")
        token = set_reset_token(user_id)
        clear_reset_token(user_id)
        user = get_user_by_reset_token(token)
        assert user is None


class TestLoginHistory:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.execute("DELETE FROM login_history")
        db.commit()
        db.close()

    def test_record_login(self):
        from auth import create_user, record_login, get_login_history
        user_id = create_user("henry", "pass123")
        record_login(user_id, "192.168.1.1", "Mozilla/5.0")
        history = get_login_history(user_id)
        assert len(history) >= 1
        assert history[0]["ip"] == "192.168.1.1"


class TestAPIKeys:
    def setup_method(self):
        os.environ["DB_PATH"] = TEST_DB
        from database_sqlite import init_db, get_db
        init_db()
        db = get_db()
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM user_profiles")
        db.execute("DELETE FROM api_keys")
        db.commit()
        db.close()

    def test_create_api_key(self):
        from auth import create_user, create_api_key, get_api_keys, verify_api_key
        user_id = create_user("iris", "pass123")
        raw_key, key_id = create_api_key(user_id, "Test Key", "read")
        assert raw_key.startswith("box5_sk_")
        assert key_id is not None

        keys = get_api_keys(user_id)
        assert len(keys) == 1
        assert keys[0]["name"] == "Test Key"

        verified = verify_api_key(raw_key)
        assert verified is not None
        assert verified["user_id"] == user_id

    def test_revoke_api_key(self):
        from auth import create_user, create_api_key, revoke_api_key, verify_api_key
        user_id = create_user("jack", "pass123")
        raw_key, key_id = create_api_key(user_id, "Revoke Me", "write")
        revoke_api_key(key_id, user_id)
        verified = verify_api_key(raw_key)
        assert verified is None

    def test_expired_api_key(self):
        from auth import create_user, create_api_key, verify_api_key
        from datetime import datetime, timedelta
        user_id = create_user("kate", "pass123")
        expired = (datetime.utcnow() - timedelta(days=1)).isoformat()
        raw_key, key_id = create_api_key(user_id, "Expired Key", "read", expired)
        verified = verify_api_key(raw_key)
        assert verified is None

    def test_invalid_api_key_format(self):
        from auth import verify_api_key
        verified = verify_api_key("invalid_key")
        assert verified is None


class TestEmailModule:
    def test_send_verification_email_mock(self):
        from mail import send_verification_email
        result = send_verification_email("test@example.com", "testuser", "token123")
        assert result is True

    def test_send_password_reset_email_mock(self):
        from mail import send_password_reset_email
        result = send_password_reset_email("test@example.com", "testuser", "token456")
        assert result is True


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    pass