import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = "/Users/Shared/ccc/project/box5/k8s/box5.db"

from database_sqlite import init_db, get_db
init_db()

import auth
import admin
USER_ID = None
ADMIN_USER_ID = None
try:
    uid = auth.create_user("admintester", "testpass123", "admin@test.com")
    admin.update_user(uid, is_admin=1)
    ADMIN_USER_ID = uid
    USER_ID = uid
except:
    pass
try:
    uid = auth.create_user("regularuser", "testpass123", "regular@test.com")
    if USER_ID is None:
        USER_ID = uid
except:
    pass

if USER_ID is None:
    row = get_db().execute("SELECT id FROM users LIMIT 1").fetchone()
    if row:
        USER_ID = row["id"]
if ADMIN_USER_ID is None:
    row = get_db().execute("SELECT user_id FROM user_profiles WHERE is_admin=1 LIMIT 1").fetchone()
    if row:
        ADMIN_USER_ID = row["user_id"]

from admin import (
    get_all_users, get_user_detail, update_user, delete_user,
    reset_user_password, get_dashboard_stats, get_all_containers,
    restart_container, delete_container, get_container_logs,
    check_quota, update_disk_usage, reduce_disk_usage
)


class TestAdminUser:
    def test_is_admin_user_admin(self):
        uid = None
        for r in admin.get_all_users(1, 1000)["users"]:
            if r["username"] == "admintester":
                uid = r["id"]
                break
        if uid is None:
            pytest.skip("admintester user not found")
        assert admin.is_admin_user(uid) is True

    def test_is_admin_user_regular(self):
        try:
            uid = auth.create_user("regularuser", "testpass123", "regular@test.com")
        except:
            uid = None
            for r in admin.get_all_users(1, 1000)["users"]:
                if r["username"] == "regularuser":
                    uid = r["id"]
                    break
        if uid is None:
            pytest.skip("regularuser not found")
        assert admin.is_admin_user(uid) is False


class TestDashboardStats:
    def test_get_dashboard_stats(self):
        stats = get_dashboard_stats()
        assert "total_users" in stats
        assert "verified_users" in stats
        assert "active_users" in stats
        assert "total_disk_bytes" in stats
        assert "running_containers" in stats
        assert "total_containers" in stats
        assert "recent_users" in stats
        assert stats["total_users"] >= 1


class TestQuotaSystem:
    def test_check_quota_user_not_found(self):
        ok, remaining = check_quota(999999)
        assert ok is True
        assert remaining == 0

    def test_update_disk_usage(self):
        if USER_ID is None:
            pytest.skip("no user available")
        update_disk_usage(USER_ID, 1000)
        reduce_disk_usage(USER_ID, 1000)

    def test_check_quota_within_limit(self):
        if USER_ID is None:
            pytest.skip("no user available")
        ok, remaining = check_quota(USER_ID, 0)
        assert ok is True
        assert remaining >= 0

    def test_check_quota_exceed(self):
        if USER_ID is None:
            pytest.skip("no user available")
        db = get_db()
        row = db.execute("SELECT quota_gb, disk_usage_bytes FROM user_profiles WHERE user_id = ?", (USER_ID,)).fetchone()
        if row is None:
            db.execute("INSERT INTO user_profiles (user_id, quota_gb, is_admin, is_active) VALUES (?, 10, 0, 1)", (USER_ID,))
            db.commit()
            row = db.execute("SELECT quota_gb, disk_usage_bytes FROM user_profiles WHERE user_id = ?", (USER_ID,)).fetchone()
        db.execute("UPDATE user_profiles SET disk_usage_bytes = 0 WHERE user_id = ?", (USER_ID,))
        db.commit()
        db.close()
        ok, remaining = check_quota(USER_ID, 200 * 1024 ** 3)
        assert ok is False


class TestUserDetail:
    def test_get_user_detail_invalid(self):
        result = get_user_detail(999999)
        assert result is None

    def test_get_user_detail_valid(self):
        result = get_user_detail(1)
        if result:
            assert "username" in result
            assert "email" in result
            assert "quota_gb" in result


class TestUserList:
    def test_get_all_users_default(self):
        result = get_all_users()
        assert "users" in result
        assert "total" in result
        assert "page" in result
        assert result["page"] == 1

    def test_get_all_users_pagination(self):
        result = get_all_users(page=2, per_page=5)
        assert result["page"] == 2
        assert result["per_page"] == 5

    def test_get_all_users_search(self):
        result = get_all_users(search="ccc")
        assert "users" in result

    def test_get_all_users_sort(self):
        result = get_all_users(sort_by="username", order="asc")
        assert "users" in result


class TestContainerManagement:
    def test_get_all_containers(self):
        containers = get_all_containers()
        assert isinstance(containers, list)

    def test_restart_nonexistent_container(self):
        ok = restart_container("nonexistent_user_xyz_123")
        assert ok is False

    def test_delete_nonexistent_container(self):
        ok = delete_container("nonexistent_user_xyz_123")
        assert ok is True

    def test_get_container_logs_nonexistent(self):
        logs = get_container_logs("nonexistent_user_xyz_123")
        assert logs == ""
