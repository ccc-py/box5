import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"

from database_sqlite import init_db
init_db()

import share as share_module
import auth


class TestShareToken:
    def test_generate_share_token(self):
        token = share_module.generate_share_token()
        assert token.startswith("share_")
        assert len(token) > 10

    def test_generate_unique_tokens(self):
        tokens = [share_module.generate_share_token() for _ in range(10)]
        assert len(set(tokens)) == 10


class TestShareCreation:
    def test_create_share_basic(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        assert share_id > 0
        assert token.startswith("share_")

    def test_create_share_with_password(self):
        share_id, token = share_module.create_share(1, "/test/file.txt", password="secret123")
        assert share_id > 0
        assert token.startswith("share_")

    def test_create_share_with_expiry(self):
        share_id, token = share_module.create_share(1, "/test/file.txt", expires_hours=1)
        assert share_id > 0


class TestShareRetrieval:
    def test_get_share_by_token(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share = share_module.get_share_by_token(token)
        assert share is not None
        assert share["token"] == token
        assert share["file_path"] == "/test/file.txt"

    def test_get_share_invalid_token(self):
        share = share_module.get_share_by_token("share_invalid_token_xyz")
        assert share is None


class TestSharePassword:
    def test_share_no_password(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share = share_module.get_share_by_token(token)
        assert share_module.check_share_password(share, "") is True
        assert share_module.check_share_password(share, "anytext") is True

    def test_share_with_password(self):
        share_id, token = share_module.create_share(1, "/test/file.txt", password="mypassword")
        share = share_module.get_share_by_token(token)
        assert share_module.check_share_password(share, "mypassword") is True
        assert share_module.check_share_password(share, "wrong") is False


class TestShareExpiry:
    def test_share_no_expiry(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share = share_module.get_share_by_token(token)
        assert share_module.is_share_expired(share) is False

    def test_share_with_expiry(self):
        from datetime import datetime, timedelta
        db = share_module.get_db()
        share_id, token = share_module.create_share(1, "/test/file.txt")
        db.execute("UPDATE shares SET expires_at = ? WHERE token = ?",
                   ((datetime.now() - timedelta(hours=1)).isoformat(), token))
        db.commit()
        db.close()
        share = share_module.get_share_by_token(token)
        assert share_module.is_share_expired(share) is True


class TestShareDownloadLimit:
    def test_share_no_limit(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share = share_module.get_share_by_token(token)
        assert share_module.is_share_download_limit_reached(share) is False

    def test_share_download_limit_reached(self):
        share_id, token = share_module.create_share(1, "/test/file.txt", max_downloads=1)
        share = share_module.get_share_by_token(token)
        share_module.increment_share_download(token)
        share = share_module.get_share_by_token(token)
        assert share_module.is_share_download_limit_reached(share) is True


class TestShareViewDownloadCount:
    def test_increment_view(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share_module.increment_share_view(token)
        share = share_module.get_share_by_token(token)
        assert share["view_count"] >= 1

    def test_increment_download(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        share_module.increment_share_download(token)
        share = share_module.get_share_by_token(token)
        assert share["download_count"] >= 1


class TestUserShares:
    def test_get_user_shares(self):
        shares = share_module.get_user_shares(1)
        assert isinstance(shares, list)

    def test_revoke_share(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        ok = share_module.revoke_share(share_id, 1)
        assert ok is True

    def test_revoke_share_wrong_user(self):
        share_id, token = share_module.create_share(1, "/test/file.txt")
        ok = share_module.revoke_share(share_id, 99999)
        assert ok is False

    def test_revoke_share_invalid_id(self):
        ok = share_module.revoke_share(99999, 1)
        assert ok is False
