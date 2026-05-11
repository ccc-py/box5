# k8s/database_sqlite.py — SQLite 資料庫連線

## 背景理論

不同於主體專案使用 sql5，k8s 版本改用標準 SQLite 搭配 WAL（Write-Ahead Logging）模式，這是因為容器環境中不需要遠端資料庫連線。

### 為何選擇 SQLite
- 容器內只有單一行程存取資料庫，不需要 client-server 架構的資料庫
- SQLite 是嵌入式資料庫，不需要額外安裝與設定
- 適合輕量級的應用場景

### WAL 模式
SQLite 的 WAL（Write-Ahead Logging）模式：
- 允許讀取與寫入同時進行，不會互相阻塞
- 提升並發效能（多執行緒同時讀取時）
- 使用 `PRAGMA journal_mode=WAL` 啟用
- 搭配 `synchronous=NORMAL` 在效能與安全性之間取得平衡

### sqlite3.Row
使用 `conn.row_factory = sqlite3.Row` 讓查詢結果可以像字典一樣透過欄位名稱存取（例如 `row["username"]`），而非僅能透過數字索引。

### 相容性介面
`start_websocket_server()` 函式保留空實作（`pass`），以維持與主體專案 `database.py` 相同的 API 簽名，方便 k8s 覆寫 main.py 的區塊內通用操作。
