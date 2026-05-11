import os
import sys
import sql5
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(SCRIPT_DIR, "box5.db"))

_websocket_process = None
_server_started = False

def start_websocket_server():
    """啟動 sql5 的 WebSocket 伺服器，監聽 8080 埠，提供持久資料庫連線"""
    global _websocket_process, _server_started
    if _server_started and _websocket_process is not None:
        return
    binary = os.environ.get("SQL5_BINARY")
    if not binary:
        from sql5._binary import get_binary_path
        binary = get_binary_path()
    _websocket_process = subprocess.Popen(
        [binary, "--websocket", "8080", DB_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(3)
    _server_started = True

def get_db():
    """透過 WebSocket 協定連線到 sql5 資料庫，回傳資料庫連線物件"""
    start_websocket_server()
    db = sql5.connect(
        path=DB_PATH,
        transport="websocket",
        host="127.0.0.1",
        port=8080
    )
    return db

def init_db():
    """初始化資料庫，建立使用者和檔案兩張資料表（若尚未存在）"""
    start_websocket_server()
    time.sleep(1)
    db = sql5.connect(
        path=DB_PATH,
        transport="websocket",
        host="127.0.0.1",
        port=8080
    )
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, filename TEXT NOT NULL, folder TEXT DEFAULT '', filepath TEXT NOT NULL, size INTEGER, is_public INTEGER, created_at TEXT, updated_at TEXT)")