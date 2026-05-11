# Docker — 應用程式容器化平台

## 概述

Docker 是一個開放原始碼的容器化平台，讓開發者可以將應用程式及其所有相依環境打包成一個輕量級、可移植的容器（container）。不同於傳統的虛擬機器（Virtual Machine, VM），Docker 容器直接運行於主機作業系統的核心（kernel）之上，不需要完整的 Guest OS，因此啟動速度快、資源開銷低。

本專案的 k8s/ 版本使用 Docker 來為每個使用者建立隔離的容器環境，實現多租戶（multi-tenant）架構。

## 核心概念

### 映像檔（Image）

映像檔是一個唯讀的模板，包含執行應用程式所需的程式碼、執行環境、系統工具與函式庫。映像檔由多層（layer）組成，每一層代表 Dockerfile 中的一條指令。這種分層架構讓映像檔可以共享基礎層，節省儲存空間與網路傳輸。

```dockerfile
FROM python:3.12-slim          # 基礎層
RUN apt-get install -y zsh     # 新增層
COPY . /app                    # 新增層
CMD ["python", "app.py"]       # 中繼資料層
```

### 容器（Container）

容器是映像檔的可執行實例（instance）。當容器啟動時，Docker 會在映像檔的唯讀層之上增加一個可寫層（container layer），所有運行時的修改（如寫入檔案）都儲存在此層。容器停止後，可寫層仍然存在，除非容器被刪除。

### 倉庫（Registry）

倉庫是儲存與分發映像檔的地方。Docker Hub 是預設的公開倉庫，而企業也可以架設私有倉庫（如 Harbor）。

## Docker 架構

### Client-Server 架構

Docker 採用 Client-Server 架構：

```
┌──────────────┐     REST API     ┌────────────────┐
│  Docker CLI  │ ◄─────────────► │  Docker Daemon  │
│  (Client)    │    (socket)     │   (dockerd)     │
└──────────────┘                 └────────────────┘
                                        │
                                        ▼
                                 ┌────────────────┐
                                 │  Containers    │
                                 │  Images        │
                                 │  Volumes       │
                                 └────────────────┘
```

- **Docker Daemon (dockerd)**：背景執行的服務，負責管理容器、映像檔、網路與儲存卷
- **Docker Client (docker CLI)**：命令列工具，透過 REST API 與 Daemon 通訊
- **Docker API**：Daemon 提供的 RESTful API，可供程式直接呼叫

### 本專案中的 Docker SDK

在 k8s/main.py 中，我們使用 Python 的 docker 套件（而非 docker CLI）來管理容器：

```python
import docker
client = docker.from_env()
container = client.containers.run(image, ...)
```

`docker.from_env()` 會從環境變數（如 `DOCKER_HOST`）讀取 Daemon 的連線設定，預設連接到本機的 Unix socket（`unix:///var/run/docker.sock`）。

## Volume 與資料持久化

### 為何需要 Volume

容器預設是可寫層的生命週期與容器綁定：容器刪除，資料也隨之消失。Volume 是 Docker 提供的資料持久化機制，讓資料獨立於容器之外。

### Volume Mount 類型

1. **Bind Mount**：將主機的目錄掛載到容器中
   ```bash
   docker run -v /host/path:/container/path ...
   ```
   特點：主機與容器共享目錄，雙方可讀寫

2. **Volume**：由 Docker 管理的儲存空間
   ```bash
   docker run -v myvolume:/data ...
   ```
   特點：由 Docker 管理，可跨容器共享

3. **tmpfs Mount**：儲存在記憶體中
   ```bash
   docker run --tmpfs /app/tmp ...
   ```
   特點：速度最快，但重啟後資料消失

### 本專案中的 Volume 設定

在 k8s 版本中，我們使用 Bind Mount 將主機的使用者目錄掛載到容器：

```python
volumes={
    os.path.abspath(UPLOAD_DIR): {"bind": "/data/uploads", "mode": "rw"},
    os.path.abspath(CONTAINER_DIR): {"bind": "/data/containers", "mode": "rw"},
    local_sync_path: {"bind": "/tmp/box5/sync", "mode": "rw"}
}
```

這讓主機與容器可以共享使用者的檔案，即使容器重啟也不會遺失資料。

## 網路模型

### Bridge 網路（預設）

Docker 安裝時會建立一個名為 `bridge` 的虛擬網路橋接器。容器啟動時（未指定 `--network`），會連接到 bridge 網路，並獲得一個私有 IP（通常在 172.17.0.0/16 範圍內）。

### Port Mapping

容器內的應用程式監聽某個連接埠（如 3111），但容器有自己的網路命名空間，外部無法直接存取。Port Mapping 將主機的某個連接埠轉發到容器的連接埠：

```bash
docker run -p 8080:3111 ...
# 主機的 8080 埠 → 容器的 3111 埠
```

在本專案中，Docker 的 `ports` 參數設定為 `{f"{SERVER_PORT}/tcp": None}`，表示由 Docker 自動分配主機的可用連接埠。

## Dockerfile

Dockerfile 是描述映像檔如何建置的文字檔案，每一條指令都對應到映像檔的一層。常見指令：

| 指令 | 用途 |
|------|------|
| `FROM` | 指定基礎映像檔 |
| `RUN` | 在容器中執行命令（建立新層） |
| `COPY` | 將本機檔案複製到映像檔 |
| `WORKDIR` | 設定工作目錄 |
| `ENV` | 設定環境變數 |
| `EXPOSE` | 宣告容器監聽的連接埠（僅作為文件用途） |
| `CMD` | 設定容器啟動時執行的命令 |

本專案的 Dockerfile.box5 採用多階段策略：先安裝系統套件與 Python 相依，再將 `database_sqlite.py` 複製為 `Server/database.py`，以 SQLite 取代 sql5。

## 容器生命週期

```
                docker create
                    │
                    ▼
              ┌──────────┐
              │  Created  │
              └──────────┘
                    │
              docker start
                    │
                    ▼
              ┌──────────┐
         ┌───►│  Running  │◄──── docker unpause
         │    └──────────┘
         │         │
   docker pause    │  docker stop
         │         │
         ▼         ▼
  ┌─────────┐ ┌──────────┐
  │ Paused  │ │ Stopped  │
  └─────────┘ └──────────┘
                    │
              docker rm
                    │
                    ▼
              ┌──────────┐
              │  Removed  │
              └──────────┘
```

## 多租戶隔離

本專案使用 Docker 來實現多租戶（multi-tenant）隔離：

- **檔案隔離**：每個使用者的檔案儲存在各自的 Volume 中
- **行程隔離**：每個使用者的應用程式在獨立的容器中執行
- **網路隔離**：每個容器有自己的網路命名空間
- **資源隔離**：可透過 `--memory`、`--cpus` 等參數限制容器資源使用

### 安全性考量

雖然 Docker 提供了一定程度的隔離，但仍有安全性考量：

1. **共用核心**：容器共用主機的 Linux 核心，若核心有漏洞可能影響所有容器
2. **Root 權限**：預設容器內以 root 執行，需透過 `--user` 限制權限
3. **Linux Capabilities**：可使用 `--cap-drop` 移除不必要的系統權限

## 常見操作

```bash
docker ps                    # 列出執行中的容器
docker ps -a                 # 列出所有容器（包含停止的）
docker images                # 列出本機映像檔
docker build -t name:tag .   # 建置映像檔
docker exec -it <id> bash    # 進入容器執行 bash
docker logs <id>             # 查看容器日誌
docker rm <id>               # 移除容器
docker rmi <id>              # 移除映像檔
docker system prune          # 清理未使用的資源
```

## 本專案參考

- k8s/ 目錄下的 `main.py` 使用 Docker SDK for Python 管理容器
- `Dockerfile.box5` 定義了使用者容器的映像檔
- Volume Mount 機制讓主機與容器共享使用者檔案
- Port Mapping 讓外部可以存取容器內的 API 服務
