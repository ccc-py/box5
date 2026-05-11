# k8s/main.py — 多租戶容器管理伺服器

## 背景理論

本檔案實作 box5 的 K8s 版本，透過 Docker API 為每個使用者建立獨立的容器（container），實現多租戶（multi-tenant）隔離。

### 多租戶架構
多租戶（Multi-Tenancy）是指單一軟體實例服務多個使用者的架構。本專案採用「每個租戶一個容器」的模式：
- 每個使用者擁有獨立的 Docker 容器
- 容器內執行 box5 Server
- 使用者之間的檔案與行程完全隔離

### Docker SDK
使用 `docker` Python 套件（而非直接呼叫 Docker CLI）來管理容器：
- `docker.from_env()` — 從環境變數讀取 Docker 設定
- `containers.run()` — 建立並啟動容器
- `containers.get()` — 取得既有容器
- `container.ports` — 查詢容器連接埠映射

### 容器生命週期管理
1. **建立**：使用者註冊或首次登入時呼叫 `create_user_container()`
2. **啟用**：啟動容器並等待 API 就緒（輪詢 `/api/health`）
3. **註冊**：在容器內部的 API 註冊使用者帳號
4. **停止**：`stop_user_container()` 停止容器
5. **刪除**：`delete_user_container()` 強制移除容器

### 連接埠分配
使用兩種方式取得使用者容器的連接埠：
- 從 `.port` 檔案讀取（持久化）
- 從 Docker 的 port mapping 查詢
- 若兩者都失敗，使用使用者名稱的 hash 值計算

### Volume Mount 同步
使用 Docker 的 volume mount 機制，將主機的 `uploads/{username}/sync` 目錄掛載到容器內的 `/tmp/box5/sync`，確保檔案在容器與主機之間同步。

### 檔案檢視器的雙重路徑
k8s 版本的檔案檢視功能支援兩種來源：
1. **容器 API**：透過使用者容器的 REST API 取得檔案資訊
2. **本機檔案系統**：直接從掛載的 volume 讀取檔案，作為備援方案
