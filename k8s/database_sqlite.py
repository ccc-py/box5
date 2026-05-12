import os
import sqlite3
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(SCRIPT_DIR, "box5.db"))
DEFAULT_USER = os.getenv("DEFAULT_USER", "ccc")

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, filename TEXT NOT NULL, folder TEXT DEFAULT '', filepath TEXT NOT NULL, size INTEGER, is_public INTEGER, created_at TEXT, updated_at TEXT)")

    db.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY REFERENCES users(id), email TEXT UNIQUE, email_verified INTEGER DEFAULT 0, verify_token TEXT, reset_token TEXT, reset_expires TEXT, quota_gb INTEGER DEFAULT 10, disk_usage_bytes INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, last_login TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), key_prefix TEXT, key_hash TEXT, name TEXT, permissions TEXT DEFAULT 'read', expires_at TEXT, created_at TEXT, revoked INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS login_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), ip TEXT, user_agent TEXT, created_at TEXT)")

    row = db.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_USER,)).fetchone()
    if row:
        db.execute("INSERT OR IGNORE INTO user_profiles (user_id, is_admin, is_active) VALUES (?, 1, 1)", (row["id"],))
        db.execute("UPDATE user_profiles SET is_admin = 1 WHERE user_id = ?", (row["id"],))

    db.commit()
    db.close()

def start_websocket_server():
    pass