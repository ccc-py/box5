# SQLite — 輕量級嵌入式關聯式資料庫

## 概述

SQLite 是一個開放原始碼的嵌入式關聯式資料庫引擎（RDBMS）。與常見的 client-server 架構資料庫（如 MySQL、PostgreSQL）不同，SQLite 以函式庫的形式直接嵌入應用程式中，不需要獨立的資料庫伺服器行程。整個資料庫就是一個普通的檔案。

本專案在 k8s 版本中使用 SQLite 搭配 WAL 模式，在主體專案中使用 sql5（一個基於 SQLite 的改良版本）。

## 設計哲學

SQLite 的設計遵循以下原則：

1. **簡單可靠**：程式碼約 15 萬行，經過 100% 分支覆蓋測試
2. **零設定**：不需要安裝、設定或管理，複製函式庫即可使用
3. **輕量級**：執行檔約 600KB，記憶體使用量極低
4. **單一檔案**：整個資料庫儲存在一個 `.db` 檔案中
5. **穩定持久**：資料庫格式向後相容至 2004 年

## 架構

```
┌─────────────────────────────────────────────┐
│                 SQL Compiler                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Tokenizer│  │  Parser  │  │ Code Gen │   │
│  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────┤
│               Virtual Machine                 │
│            (VDBE - bytecode engine)           │
├─────────────────────────────────────────────┤
│                  B-Tree                       │
├─────────────────────────────────────────────┤
│                  Pager                        │
├─────────────────────────────────────────────┤
│               OS Interface                    │
│           (File I/O, Locking)                 │
└─────────────────────────────────────────────┘
```

### 查詢執行流程

1. **Tokenizer**：將 SQL 字串分解為 token（關鍵字、識別字、運算子等）
2. **Parser**：根據 SQL 語法規則將 token 組合成解析樹（parse tree）
3. **Code Generator**：將解析樹轉換為 VDBE（Virtual Database Engine）的 bytecode
4. **VDBE**：執行 bytecode 程式，操作 B-Tree 進行資料存取
5. **Pager**：管理記憶體中的頁面快取（page cache），處理事務與鎖定
6. **OS Interface**：透過作業系統的檔案 I/O 讀寫資料庫檔案

## 資料型別

SQLite 使用動態型別系統（manifest typing），與其他資料庫的靜態型別不同：

| 型別 | 說明 | 範例 |
|------|------|------|
| `NULL` | 空值 | `NULL` |
| `INTEGER` | 有號整數（1~8 bytes） | `42` |
| `REAL` | 浮點數（8 bytes IEEE） | `3.14` |
| `TEXT` | 字串（UTF-8/16） | `'hello'` |
| `BLOB` | 二進位資料 | `x'FF00'` |

與 MySQL 不同，SQLite 的 `VARCHAR(255)` 實際上只是一個 `TEXT`，不會檢查長度限制。

## 事務（Transaction）

SQLite 使用 MVCC（Multi-Version Concurrency Control）來管理事務：

### 事務狀態

```
         ┌──────────┐
         │  UNLOCKED │
         └──────────┘
              │
              ▼
         ┌──────────┐
         │  SHARED   │  ← 讀取事務
         └──────────┘
              │
              ▼
         ┌──────────┐
         │ RESERVED  │  ← 準備寫入
         └──────────┘
              │
              ▼
         ┌──────────┐
         │ PENDING   │  ← 等待其他讀取完成
         └──────────┘
              │
              ▼
         ┌──────────┐
         │ EXCLUSIVE │  ← 實際寫入
         └──────────┘
```

### 鎖定層級

- **UNLOCKED**：未進行任何操作
- **SHARED**：讀取鎖定，允許其他連線同時讀取
- **RESERVED**：準備寫入，但仍允許讀取
- **PENDING**：等待獲得 EXCLUSIVE 鎖定，不再允許新的 SHARED 鎖定
- **EXCLUSIVE**：獨佔鎖定，僅允許寫入操作

## WAL 模式（Write-Ahead Logging）

### 傳統日誌模式（Journal Mode）

在傳統的 `DELETE` 日誌模式中，寫入操作時會將原始頁面複製到日誌檔（rollback journal），然後修改資料庫。若寫入中斷，可從日誌檔恢復。這種模式下，讀取與寫入會互相阻塞。

### WAL 模式的運作原理

WAL 模式改變了寫入策略：

```
傳統模式：
  UPDATE users SET name='Alice' → 直接修改 database 檔案
  （讀取者必須等待寫入完成）

WAL 模式：
  UPDATE users SET name='Alice' → 追加到 .wal 檔案
  讀取者繼續讀取 database 檔案（舊資料）
  Checkpoint → 將 .wal 中的修改合併回 database 檔案
```

### WAL 的優點

1. **讀寫不互斥**：讀取者可讀取舊版本資料，寫入者同時在 WAL 檔案寫入新資料
2. **寫入效能提升**：順序寫入 WAL 檔案比隨機寫入 database 檔案快
3. **讀取效能略降**：需要檢查 WAL 檔案是否有更新的版本

### 本專案中的 WAL 設定

在 `k8s/database_sqlite.py` 中：

```python
conn.execute("PRAGMA journal_mode=WAL")    # 啟用 WAL 模式
conn.execute("PRAGMA synchronous=NORMAL")  # 設定同步模式
```

- `synchronous=FULL`：最安全但最慢，每次寫入都等待資料寫入磁碟
- `synchronous=NORMAL`：平衡安全性與效能，WAL 模式下等同於 FULL
- `synchronous=OFF`：最快但可能在崩潰時損毀資料

## SQLite 限制

### 不適合的場景

1. **高並發寫入**：SQLite 同時只允許一個寫入事務
2. **分散式系統**：不支援網路存取，無法跨機器使用
3. **大量資料**：單一資料庫檔案不建議超過 140TB（實際上數十 GB 就開始效能下降）
4. **使用者權限管理**：不支援 MySQL/PostgreSQL 那樣的細粒度權限控制

### 本專案中的因應策略

k8s 版本為每個使用者建立獨立的 SQLite 資料庫檔案，避免多使用者並發寫入的競爭問題。每個使用者的資料庫檔案位於 `uploads/{username}/box5.db`。

## 實用操作

```sql
-- 查看資料庫資訊
PRAGMA database_list;
PRAGMA page_count;
PRAGMA page_size;

-- 查看所有表格
.tables

-- 查看表格結構
.schema users

-- 啟用/停用設定
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-8000;  -- 8MB 快取

-- 執行 VACUUM 回收空間
VACUUM;
```

## sql5 — 本專案的資料庫

本專案的主體版本使用 sql5 而非直接使用 SQLite。sql5 是基於 SQLite 的包裝，提供了 WebSocket 傳輸協定，讓應用程式可以透過網路連線到 SQLite 資料庫。

```python
# sql5 的 WebSocket 模式
db = sql5.connect(
    path=DB_PATH,
    transport="websocket",
    host="127.0.0.1",
    port=8080
)
```

這解決了 SQLite 原生的兩個限制：
1. **行程隔離**：每個連線都是獨立 process，WebSocket 模式維持持久連線
2. **網路存取**：允許應用程式與資料庫不在同一行程中

k8s 版本則直接使用標準 SQLite，因為容器內部不需要網路連線資料庫。
