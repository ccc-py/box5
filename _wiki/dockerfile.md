# Dockerfile — Docker 映像檔建置腳本

## 概述

Dockerfile 是一個文字檔案，包含建立 Docker 映像檔（image）所需的指令。每一條指令對應到映像檔的一層（layer），Docker 會快取這些層以加速後續建置。

本專案的 `Dockerfile.box5` 定義了使用者執行 box5 伺服器所需的環境。

## Dockerfile 指令大全

### FROM — 基礎映像檔

`FROM` 指定建置的起點，可以是作業系統（如 `ubuntu:22.04`）或預裝好執行環境的映像檔（如 `python:3.12-slim`）：

```dockerfile
FROM python:3.12-slim
```

`python:3.12-slim` 基於 Debian slim 版本，體積較小（約 120MB），只包含執行 Python 所需的最小套件集。

### RUN — 執行命令

`RUN` 在容器中執行命令，並將結果儲存為新層：

```dockerfile
RUN apt-get update && apt-get install -y \
    git \
    curl \
    sqlite3 \
    zsh \
    && rm -rf /var/lib/apt/lists/*
```

**重要**：使用 `&&` 串聯多個命令，並在最後清理快取，以減少最終映像檔的大小。每一個 `RUN` 指令都會新增一層，因此合併相關命令可以減少層數。

### COPY — 複製檔案

`COPY` 將建置環境（context）中的檔案複製到映像檔中：

```dockerfile
COPY database_sqlite.py /tmp/box5/Server/database.py
```

`COPY` 只複製，不解壓縮或下載。若需要從 URL 下載，使用 `ADD` 指令。

### WORKDIR — 設定工作目錄

`WORKDIR` 設定後續指令的執行目錄：

```dockerfile
WORKDIR /tmp/box5
```

若目錄不存在，會自動建立。後續的 `RUN`、`CMD`、`COPY` 等指令都會以此為基礎路徑。

### ENV — 設定環境變數

`ENV` 設定容器中的環境變數：

```dockerfile
ENV PORT=3111
ENV PYTHONPATH=/tmp/box5
ENV DB_PATH=/data/uploads/ccc/box5.db
```

這些變數在容器運行期間始終有效，可被應用程式讀取。

### EXPOSE — 宣告連接埠

`EXPOSE` 宣告容器監聽的連接埠（僅作為文件用途，不實際開啟埠）：

```dockerfile
EXPOSE 3111
```

實際的連接埠映射需要在 `docker run -p` 或 Docker Compose 中設定。

### CMD — 啟動命令

`CMD` 設定容器啟動時預設執行的命令：

```dockerfile
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3111"]
```

`CMD` 有三種格式：
- **Exec 格式**（建議）：`CMD ["executable", "param1", "param2"]`
- **Shell 格式**：`CMD command param1 param2`
- **參數格式**：`CMD ["param1", "param2"]`（搭配 ENTRYPOINT 使用）

Exec 格式不會啟動 shell，因此訊號（如 SIGTERM）可以直接傳遞給程序，實現優雅關閉。

### ENTRYPOINT — 進入點

`ENTRYPOINT` 與 `CMD` 類似，但不可被 `docker run` 的命令列參數覆蓋：

```dockerfile
ENTRYPOINT ["python"]
CMD ["-m", "uvicorn", "main:app"]
```

搭配使用時，`docker run myimage -c "print('hello')"` 會執行 `python -c "print('hello')"`。

## 多階段建置（Multi-stage Build）

多階段建置允許在同一個 Dockerfile 中使用多個 `FROM` 指令，只有最後一個階段的內容會包含在最終映像檔中：

```dockerfile
# 階段一：建置環境
FROM python:3.12 AS builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 階段二：執行環境
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app
CMD ["python", "app.py"]
```

優點：
- 最終映像檔只包含執行所需的檔案，不含建置工具
- 大幅減小映像檔體積

## 本專案的 Dockerfile.box5

```dockerfile
FROM python:3.12-slim

# 1. 安裝系統套件
RUN apt-get update && apt-get install -y \
    git curl sqlite3 zsh \
    && rm -rf /var/lib/apt/lists/*

# 2. 安裝 uv
RUN pip install --no-cache-dir uv

# 3. 複製原始碼
RUN git clone https://github.com/ccc-py/box5.git /tmp/box5

# 4. 設定工作目錄
WORKDIR /tmp/box5

# 5. 安裝 Python 相依套件
RUN printf "fastapi>=0.100.0\nuvicorn[standard]>=0.23.0\npydantic>=2.0.0\npython-multipart>=0.0.6\nrequests>=2.31.0\nwatchdog>=4.0.0\nmarkdown>=3.5.0" > requirements.txt
RUN uv pip install --system -r requirements.txt

# 6. 用 SQLite 版本取代 sql5 版本
WORKDIR /tmp/box5/Server
COPY database_sqlite.py /tmp/box5/Server/database.py

# 7. 設定環境變數
ENV PORT=3111
ENV PYTHONPATH=/tmp/box5
ENV DB_PATH=/data/uploads/ccc/box5.db

EXPOSE 3111

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3111"]
```

### 設計考量

**為什麼沒有 UV 同步**：容器內使用 `uv pip install --system` 而非 `uv sync`，因為不需要虛擬環境隔離（容器本身就是隔離的）。

**為什麼複製 database_sqlite.py**：容器內不需要 sql5 的 WebSocket 資料庫連線，改用標準 SQLite 減少相依。

**為什麼安裝 zsh**：WebSocket 終端機功能使用 zsh 作為使用者的預設 shell。

**為什麼從 GitHub 複製原始碼**：使用 `git clone` 確保取得最新版本，也可改為 `COPY . /tmp/box5` 使用本機檔案。

## 最佳實踐

### 減少層數

```dockerfile
# 不好：多層
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2
RUN rm -rf /var/lib/apt/lists/*

# 好：單層
RUN apt-get update && apt-get install -y \
    package1 package2 \
    && rm -rf /var/lib/apt/lists/*
```

### 利用快取

Docker 會快取每一層。將較少變動的層放在前面：

```dockerfile
# 1. 基礎映像檔（幾乎不變）
FROM python:3.12-slim

# 2. 系統套件（偶爾變動）
RUN apt-get update && apt-get install -y zsh

# 3. 相依套件（依賴變動時才變）
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. 應用程式碼（經常變動）
COPY . /app
```

### 最小權限原則

```dockerfile
# 建立非 root 使用者
RUN useradd -m -s /bin/bash box5
USER box5
```

### HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:3111/health || exit 1
```

讓 Docker 可以自動偵測容器健康狀態。

## 建置與執行

```bash
# 建置映像檔
docker build -t box5-server:latest -f Dockerfile.box5 .

# 執行容器
docker run -d \
    --name box5-ccc \
    -p 20001:3111 \
    -v /path/to/uploads:/data/uploads \
    box5-server:latest
```

## 本專案參考

- `k8s/Dockerfile.box5` 定義了使用者容器的映像檔
- `k8s/main.py` 使用 Docker SDK 動態建立容器
- 容器內的 `Server/database.py` 被 `database_sqlite.py` 覆蓋
