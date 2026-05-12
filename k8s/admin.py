from database_sqlite import get_db
import docker
import os

CONTAINER_IMAGE = os.getenv("BOX5_IMAGE", "box5-server:latest")


def is_admin_user(user_id: int) -> bool:
    db = get_db()
    row = db.execute("SELECT is_admin FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    db.close()
    return row and row["is_admin"] == 1


def get_all_users(page: int = 1, per_page: int = 20, search: str = "", sort_by: str = "created_at", order: str = "desc"):
    db = get_db()
    offset = (page - 1) * per_page
    conditions = []
    params = []
    if search:
        conditions.append("(u.username LIKE ? OR up.email LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    valid_sorts = {"username": "u.username", "email": "up.email", "created_at": "u.created_at", "last_login": "up.last_login", "disk_usage_bytes": "up.disk_usage_bytes"}
    sort_col = valid_sorts.get(sort_by, "u.created_at")
    sort_dir = "DESC" if order.lower() == "desc" else "ASC"

    total = db.execute(f"SELECT COUNT(*) as cnt FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id {where}", params).fetchone()["cnt"]

    rows = db.execute(f"""
        SELECT u.id, u.username, u.created_at, up.email, up.email_verified,
               up.quota_gb, up.disk_usage_bytes, up.is_admin, up.is_active, up.last_login
        FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id
        {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT ? OFFSET ?
    """, params + [per_page, offset]).fetchall()
    db.close()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "username": r["username"],
            "created_at": r["created_at"],
            "email": r["email"],
            "email_verified": bool(r["email_verified"]),
            "quota_gb": r["quota_gb"],
            "disk_usage_bytes": r["disk_usage_bytes"],
            "is_admin": bool(r["is_admin"]),
            "is_active": bool(r["is_active"]),
            "last_login": r["last_login"],
        })
    return {"users": users, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


def get_user_detail(user_id: int):
    db = get_db()
    row = db.execute("""
        SELECT u.id, u.username, u.created_at, up.email, up.email_verified,
               up.quota_gb, up.disk_usage_bytes, up.is_admin, up.is_active, up.last_login
        FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = ?
    """, (user_id,)).fetchone()
    db.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
        "email": row["email"],
        "email_verified": bool(row["email_verified"]),
        "quota_gb": row["quota_gb"],
        "disk_usage_bytes": row["disk_usage_bytes"],
        "is_admin": bool(row["is_admin"]),
        "is_active": bool(row["is_active"]),
        "last_login": row["last_login"],
    }


def update_user(user_id: int, quota_gb: int = None, is_active: int = None, is_admin: int = None):
    db = get_db()
    sets = []
    params = []
    if quota_gb is not None:
        sets.append("quota_gb = ?")
        params.append(quota_gb)
    if is_active is not None:
        sets.append("is_active = ?")
        params.append(is_active)
    if is_admin is not None:
        sets.append("is_admin = ?")
        params.append(is_admin)
    if not sets:
        db.close()
        return
    params.append(user_id)
    db.execute(f"UPDATE user_profiles SET {', '.join(sets)} WHERE user_id = ?", params)
    db.commit()
    db.close()


def delete_user(user_id: int) -> bool:
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        db.close()
        return False
    username = user["username"]

    container_name = f"box5-{username}"
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.remove(force=True)
    except:
        pass

    user_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", username)
    if os.path.exists(user_dir):
        import shutil
        shutil.rmtree(user_dir, ignore_errors=True)

    db.execute("DELETE FROM login_history WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    db.close()
    return True


def reset_user_password(user_id: int, new_password: str) -> bool:
    from auth import hash_password, update_user_password
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if not user:
        return False

    password_hash = hash_password(new_password)
    update_user_password(user_id, new_password)

    try:
        container_name = f"box5-{user['username']}"
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.exec_run(f"bash -c 'echo {user['username']}:{new_password} | chpasswd'")
    except Exception as e:
        print(f"Warning: Could not sync container password: {e}")

    return True


def get_dashboard_stats():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    verified_users = db.execute("SELECT COUNT(*) as cnt FROM user_profiles WHERE email_verified = 1").fetchone()["cnt"]
    active_users = db.execute("SELECT COUNT(*) as cnt FROM user_profiles WHERE is_active = 1").fetchone()["cnt"]
    total_disk = db.execute("SELECT COALESCE(SUM(disk_usage_bytes), 0) as total FROM user_profiles").fetchone()["total"]

    try:
        client = docker.from_env()
        running_containers = len([c for c in client.containers.list() if c.name and c.name.startswith("box5-") and c.status == "running"])
        total_containers = len([c for c in client.containers.list() if c.name and c.name.startswith("box5-")])
    except:
        running_containers = 0
        total_containers = 0

    recent_users = db.execute("""
        SELECT u.id, u.username, u.created_at, up.email, up.is_active
        FROM users u LEFT JOIN user_profiles up ON u.id = up.user_id
        ORDER BY u.created_at DESC LIMIT 10
    """).fetchall()

    db.close()

    recent_list = []
    for r in recent_users:
        recent_list.append({
            "id": r["id"],
            "username": r["username"],
            "created_at": r["created_at"],
            "email": r["email"],
            "is_active": bool(r["is_active"]),
        })

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "active_users": active_users,
        "total_disk_bytes": total_disk,
        "running_containers": running_containers,
        "total_containers": total_containers,
        "recent_users": recent_list,
    }


def get_all_containers():
    try:
        client = docker.from_env()
        containers = []
        for c in client.containers.list(all=True):
            if c.name and c.name.startswith("box5-"):
                username = c.name.replace("box5-", "")
                containers.append({
                    "name": c.name,
                    "username": username,
                    "status": c.status,
                    "created": str(c.attrs.get("Created", "")),
                    "ports": str(c.ports),
                })
        return containers
    except Exception as e:
        return []


def restart_container(username: str) -> bool:
    try:
        client = docker.from_env()
        container_name = f"box5-{username}"
        container = client.containers.get(container_name)
        container.restart()
        return True
    except:
        return False


def delete_container(username: str) -> bool:
    try:
        client = docker.from_env()
        container_name = f"box5-{username}"
        container = client.containers.get(container_name)
        container.remove(force=True)
        return True
    except docker.errors.NotFound:
        return True
    except:
        return False


def get_container_logs(username: str, lines: int = 100):
    try:
        client = docker.from_env()
        container_name = f"box5-{username}"
        container = client.containers.get(container_name)
        logs = container.logs(tail=lines).decode("utf-8", errors="ignore")
        return logs
    except:
        return ""


def update_disk_usage(user_id: int, file_size: int):
    db = get_db()
    db.execute("UPDATE user_profiles SET disk_usage_bytes = disk_usage_bytes + ? WHERE user_id = ?", (file_size, user_id))
    db.commit()
    db.close()


def reduce_disk_usage(user_id: int, file_size: int):
    db = get_db()
    db.execute("UPDATE user_profiles SET disk_usage_bytes = MAX(0, disk_usage_bytes - ?) WHERE user_id = ?", (file_size, user_id))
    db.commit()
    db.close()


def check_quota(user_id: int, additional_bytes: int = 0) -> tuple[bool, int]:
    db = get_db()
    row = db.execute("SELECT quota_gb, disk_usage_bytes FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    db.close()
    if not row:
        return True, 0
    quota_bytes = row["quota_gb"] * (1024 ** 3)
    current_usage = row["disk_usage_bytes"]
    if current_usage + additional_bytes > quota_bytes:
        return False, quota_bytes - current_usage
    return True, quota_bytes - current_usage - additional_bytes
