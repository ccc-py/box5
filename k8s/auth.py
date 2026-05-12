import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from passlib.hash import bcrypt
from jose import jwt, JWTError

from database_sqlite import get_db

SECRET_KEY = os.getenv("JWT_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 24 * 60 * 60

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=ACCESS_TOKEN_EXPIRE)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_verify_token() -> str:
    return secrets.token_urlsafe(32)


def create_reset_token() -> str:
    return secrets.token_urlsafe(32)


def generate_api_key() -> tuple[str, str]:
    raw = f"box5_sk_{secrets.token_hex(24)}"
    key_prefix = raw[:16]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash, key_prefix


def get_user_by_username(username: str) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_user_profile(user_id: int) -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def create_user(username: str, password: str, email: str = "") -> Optional[int]:
    if get_user_by_username(username):
        return None

    db = get_db()
    password_hash = hash_password(password)
    created_at = datetime.utcnow().isoformat()

    cursor = db.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, created_at)
    )
    user_id = cursor.lastrowid

    verify_token = create_verify_token() if email else None
    db.execute(
        "INSERT INTO user_profiles (user_id, email, verify_token) VALUES (?, ?, ?)",
        (user_id, email or None, verify_token)
    )
    db.commit()
    db.close()
    return user_id


def update_user_password(user_id: int, new_password: str) -> bool:
    db = get_db()
    password_hash = hash_password(new_password)
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    db.commit()
    db.close()
    return True


def verify_user_email(user_id: int) -> bool:
    db = get_db()
    db.execute("UPDATE user_profiles SET email_verified = 1, verify_token = NULL WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()
    return True


def set_reset_token(user_id: int) -> str:
    db = get_db()
    token = create_reset_token()
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    db.execute("UPDATE user_profiles SET reset_token = ?, reset_expires = ? WHERE user_id = ?", (token, expires, user_id))
    db.commit()
    db.close()
    return token


def get_user_by_reset_token(token: str) -> Optional[dict]:
    db = get_db()
    row = db.execute(
        "SELECT u.*, up.reset_expires FROM users u JOIN user_profiles up ON u.id = up.user_id WHERE up.reset_token = ?",
        (token,)
    ).fetchone()
    db.close()
    if not row:
        return None
    user = dict(row)
    if user.get("reset_expires"):
        expires = datetime.fromisoformat(user["reset_expires"])
        if datetime.utcnow() > expires:
            return None
    return user


def clear_reset_token(user_id: int) -> bool:
    db = get_db()
    db.execute("UPDATE user_profiles SET reset_token = NULL, reset_expires = NULL WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()
    return True


def record_login(user_id: int, ip: str, user_agent: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO login_history (user_id, ip, user_agent, created_at) VALUES (?, ?, ?, ?)",
        (user_id, ip, user_agent, datetime.utcnow().isoformat())
    )
    db.execute("UPDATE user_profiles SET last_login = ? WHERE user_id = ?", (datetime.utcnow().isoformat(), user_id))
    db.commit()
    db.close()


def get_login_history(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM login_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def create_api_key(user_id: int, name: str, permissions: str = "read", expires_at: str = "") -> tuple[str, int]:
    raw_key, key_hash, key_prefix = generate_api_key()
    db = get_db()
    cursor = db.execute(
        "INSERT INTO api_keys (user_id, key_prefix, key_hash, name, permissions, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, key_prefix, key_hash, name, permissions, expires_at or None, datetime.utcnow().isoformat())
    )
    db.commit()
    db.close()
    return raw_key, cursor.lastrowid


def get_api_keys(user_id: int) -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT id, key_prefix, name, permissions, expires_at, created_at, revoked FROM api_keys WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def revoke_api_key(key_id: int, user_id: int) -> bool:
    db = get_db()
    db.execute("UPDATE api_keys SET revoked = 1 WHERE id = ? AND user_id = ?", (key_id, user_id))
    db.commit()
    db.close()
    return True


def verify_api_key(raw_key: str) -> Optional[dict]:
    if not raw_key.startswith("box5_sk_"):
        return None
    db = get_db()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = db.execute("SELECT * FROM api_keys WHERE key_hash = ? AND revoked = 0", (key_hash,)).fetchone()
    db.close()
    if not row:
        return None
    key_info = dict(row)
    if key_info.get("expires_at"):
        expires = datetime.fromisoformat(key_info["expires_at"])
        if datetime.utcnow() > expires:
            return None
    return key_info


def is_email_verified(user_id: int) -> bool:
    profile = get_user_profile(user_id)
    return profile and profile.get("email_verified") == 1