import os
import secrets
import hashlib
from datetime import datetime, timedelta
from database_sqlite import get_db
from auth import hash_password, verify_password


def generate_share_token() -> str:
    return f"share_{secrets.token_urlsafe(24)}"


def create_share(user_id: int, file_path: str, password: str = "", expires_hours: int = 0, max_downloads: int = 0) -> tuple[int, str]:
    db = get_db()
    token = generate_share_token()
    password_hash = hash_password(password) if password else None
    expires_at = None
    if expires_hours > 0:
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
    created_at = datetime.now().isoformat()
    cursor = db.execute("""
        INSERT INTO shares (user_id, file_path, token, password_hash, expires_at, max_downloads, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, file_path, token, password_hash, expires_at, max_downloads if max_downloads > 0 else None, created_at))
    db.commit()
    share_id = cursor.lastrowid
    db.close()
    return share_id, token


def get_share_by_token(token: str):
    db = get_db()
    row = db.execute("SELECT * FROM shares WHERE token = ? AND revoked = 0", (token,)).fetchone()
    db.close()
    if not row:
        return None
    return dict(row)


def is_share_expired(share) -> bool:
    if not share["expires_at"]:
        return False
    try:
        expires = datetime.fromisoformat(share["expires_at"])
        return datetime.now() > expires
    except:
        return True


def is_share_download_limit_reached(share) -> bool:
    if not share["max_downloads"]:
        return False
    return share["download_count"] >= share["max_downloads"]


def check_share_password(share, password: str) -> bool:
    if not share["password_hash"]:
        return True
    return verify_password(password, share["password_hash"])


def increment_share_download(token: str) -> bool:
    db = get_db()
    db.execute("UPDATE shares SET download_count = download_count + 1 WHERE token = ?", (token,))
    db.commit()
    db.close()
    return True


def increment_share_view(token: str) -> bool:
    db = get_db()
    db.execute("UPDATE shares SET view_count = view_count + 1 WHERE token = ?", (token,))
    db.commit()
    db.close()
    return True


def get_user_shares(user_id: int):
    db = get_db()
    rows = db.execute("""
        SELECT id, file_path, token, password_hash, expires_at, max_downloads,
               download_count, view_count, created_at, revoked
        FROM shares WHERE user_id = ? AND revoked = 0 ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    db.close()
    shares = []
    for r in rows:
        shares.append({
            "id": r["id"],
            "file_path": r["file_path"],
            "token": r["token"],
            "has_password": bool(r["password_hash"]),
            "expires_at": r["expires_at"],
            "max_downloads": r["max_downloads"],
            "download_count": r["download_count"],
            "view_count": r["view_count"],
            "created_at": r["created_at"],
            "revoked": bool(r["revoked"]),
        })
    return shares


def revoke_share(share_id: int, user_id: int) -> bool:
    db = get_db()
    row = db.execute("SELECT id FROM shares WHERE id = ? AND user_id = ?", (share_id, user_id)).fetchone()
    if not row:
        db.close()
        return False
    db.execute("UPDATE shares SET revoked = 1 WHERE id = ?", (share_id,))
    db.commit()
    db.close()
    return True
