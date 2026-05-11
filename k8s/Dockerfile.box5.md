# k8s/Dockerfile.box5 — 使用者容器映像檔

## 背景理論

Docker 容器映像檔（image）是一個輕量級、可獨立執行的軟體套件，包含執行程式所需的一切：程式碼、執行環境、系統工具與函式庫。

### 基礎映像檔
使用 `python:3.12-slim` 作為基礎，因為：
- Debian slim 版本體積小（約 100MB）
- 預裝 Python 3.12，減少手動安裝的步驟
- 使用 `apt-get` 安裝 git、curl、sqlite3、zsh 等額外工具

### 安裝流程
1. 安裝系統套件（git、curl、sqlite3、zsh）
2. 使用 pip 安裝 uv（Python 套件管理器）
3. 從 GitHub 複製 box5 原始碼
4. 建立 requirements.txt 並用 uv 安裝相依套件
5. 將 `database_sqlite.py` 複製為 `Server/database.py`，覆蓋 sql5 版本

### 為什麼要覆蓋 database.py
容器內的 Server 不需要 sql5 的 WebSocket 資料庫連線，因此用 `database_sqlite.py`（使用標準 SQLite）來取代原本的 `Server/database.py`（使用 sql5）。這樣容器就可以在不需要額外 sql5 二進位檔的情況下正常運作。

### 環境變數
- `PORT=3111` — 容器內伺服器監聽埠
- `PYTHONPATH=/tmp/box5` — 讓 Python 找到 box5 模組
- `DB_PATH=/data/uploads/ccc/box5.db` — 資料庫檔案路徑（位於 volume mount 目錄）

### 啟動命令
使用 `uvicorn` 啟動 FastAPI 應用程式：
```
python -m uvicorn main:app --host 0.0.0.0 --port 3111
```
監聽所有網路介面（0.0.0.0）以便 Docker 的 port mapping 可以正確轉發請求到容器。
