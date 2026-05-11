# Server/database.py — 資料庫連線管理

## 背景理論

本專案使用 sql5 作為資料庫引擎。sql5 是一個基於 SQLite 的資料庫系統，提供 WebSocket 傳輸協定，讓客戶端可以透過網路連線資料庫。

### 為何使用 WebSocket 模式
- **持久連線**：一般 SQLite server 模式中，每個連線都是獨立 process，使用 WebSocket 模式可以維持持久連線
- **遠端存取**：允許應用程式與資料庫不在同一行程（process）中

### 啟動流程
1. `start_websocket_server()` — 啟動 sql5 的 WebSocket 伺服器，監聽 port 8080
2. `get_db()` — 回傳一個透過 WebSocket 連線到 sql5 的資料庫連線
3. `init_db()` — 建立 `users` 與 `files` 兩張資料表

### 資料表架構
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    folder TEXT DEFAULT '',
    filepath TEXT NOT NULL,
    size INTEGER,
    is_public INTEGER,
    created_at TEXT,
    updated_at TEXT
);
```

### sql5 二進位檔路徑
系統優先使用 `SQL5_BINARY` 環境變數指定的路徑，否則從 sql5 Python 套件中取得預設路徑。這使得開發者可以指定自訂版本的 sql5 二進位檔進行測試。
