# Box5 Docker 隔離版（k8s）

一個使用 Docker 容器隔離每位使用者的檔案管理系統。

## 功能特色

- 使用者註冊後自動建立獨立 Docker 容器
- 每位使用者擁有完全隔離的環境
- 檔案上傳、下載、檢視、編輯
- Markdown 渲染（帶路徑標題）
- 網頁編輯器（Monaco Editor + 終端機）
- 終端機：WebSocket 遠端 zsh Shell
- 支援本機同步用戶端，不需 Docker 也能使用

---

# 第一部分：Server 端（經營者）

## 快速啟動

### 1. 建置 Docker 映像檔（首次）

```bash
cd k8s
docker build -t box5-server:latest -f Dockerfile.box5 .
```

### 2. 啟動伺服器

```bash
./k8s_run.sh
```

或手動啟動：
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. 開啟網站

```
http://localhost:8000
```

預設帳號：`ccc` / `cccpass`

## Server 架構

```
使用者請求 → k8s/main.py (port 8000) → 轉發到該用戶的 Docker 容器 (port 311xx)
```

每位使用者有獨立的 Docker 容器，容器內跑獨立的 Box5 Server，完全隔離。

## 管理者功能

登入後進入 `/admin` 可使用：

- **管理儀表板** `/admin` — 查看使用者數、容器狀態、磁碟用量
- **使用者管理** `/admin/users` — 列表、搜尋、配額調整、啟用/停用、刪除、重設密碼
- **容器管理** `/admin/containers` — 容器列表、重啟、刪除、查看日誌

## 公開檔案功能

放在 `sync/public/` 下的檔案，**任何人都能直接存取**，不需要登入：

```
http://localhost:8000/api/public/files
```

## Server 端環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `BOX5_IMAGE` | Docker 映像檔 | box5-server:latest |
| `BOX5_HOST` | 主機位址 | localhost |
| `BOX5_SSH_BASE_PORT` | SSH 起始埠號 | 22000 |
| `DEFAULT_USER` | 預設建立的使用者 | ccc |
| `DEFAULT_PASS` | 預設使用者密碼 | cccpass |
| `DB_PATH` | 資料庫路徑 | k8s/box5.db |
| `SMTP_HOST` | SMTP 主機（寄信用） | - |
| `SMTP_PORT` | SMTP 連接埠 | 587 |
| `SMTP_USER` | SMTP 帳號 | - |
| `SMTP_PASS` | SMTP 密碼 | - |
| `EMAIL_FROM` | 寄件人信箱 | - |
| `BASE_URL` | 網站基底 URL | - |
| `JWT_SECRET` | JWT 密鑰 | - |

---

# 第二部分：Client 端（一般使用者）

## 兩種使用方式

### 方式一：網頁操作（需 Docker）

1. 註冊帳號 → 系統自動建立 Docker 容器
2. 登入後透過網頁上傳、下載、檢視檔案
3. 編輯器：`/editor`

**適用對象：** 需要完整隔離環境、SSH 存取的使用者

### 方式二：本機同步用戶端（不需 Docker）

直接連接 Server，本機指定資料夾自動雙向同步。

**適用對象：** 不想用 Docker、只想同步檔案的使用者

## Client 端環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `BOX5_SERVER` | Server URL | http://localhost:8000 |
| `BOX5_FOLDER` | 本機同步資料夾 | ./sync |
| `BOX5_USER` | 帳號 | - |
| `BOX5_PASS` | 密碼 | - |

## 啟動同步用戶端

```bash
cd k8s
python sync_client.py --server http://localhost:8000 \
  --user 你的帳號 --password 你的密碼 \
  --folder ./sync
```

或先設定環境變數：

```bash
export BOX5_SERVER=http://localhost:8000
export BOX5_USER=ccc
export BOX5_PASS=cccpass
export BOX5_FOLDER=./sync
python sync_client.py
```

## 同步模式

啟動後選擇模式：

```
1) Watch 模式（預設）— 雙向即時同步，監控本機資料夾變化
2) Pull 模式            — 只從伺服器下載檔案
3) Push 模式            — 只上傳本機檔案
4) Full Sync            — 上傳後進入 Watch 模式
```

## 同步邏輯

```
本機 sync/              →  同步到遠端 /           （需登入，私人）
本機 sync/public/       →  同步到遠端 /public/    （公開，任何人可存取）
```

## 檔案結構

```
sync/                    ← 本機同步資料夾（預設名稱，可自訂）
├── file1.txt           ← 私人檔案
├── docs/
│   └── readme.md        ← 私人檔案
└── public/             ← 公開資料夾
    ├── image.png         ← 公開圖片
    └── report.pdf        ← 公開文件
```

## 公開檔案

放在 `sync/public/` 下的檔案會同步到 Server 的 `/public/` 資料夾，**任何人都能直接下載**，URL：

```
http://你的Server/api/public/files
```

---

# 第三部分：網站功能

## 檔案類型與顯示方式

| 副檔名 | 顯示方式 |
|--------|----------|
| `.md` | Markdown 渲染 + 路徑標題 |
| `.html` | 直接渲染 HTML |
| `.jpg` `.png` `.gif` `.webp` `.svg` `.pdf` | 直接顯示圖片/PDF |
| `.py` `.js` `.ts` `.sh` `.c` `.go` `.rs` 等 | 程式碼區塊（帶路徑標題） |
| `.txt` | 純文字 |
| 其他 | 下載 |

## 頁面路由

| 路徑 | 說明 |
|------|------|
| `/` | 檔案列表（需登入） |
| `/login` | 登入 |
| `/register` | 註冊（自動建立容器） |
| `/logout` | 登出 |
| `/view/路徑` | 瀏覽檔案 |
| `/download/ID` | 下載檔案 |
| `/history/ID` | 歷史記錄 |
| `/editor` | 線上編輯器（Monaco + 終端機） |
| `/admin` | 管理儀表板（需 admin 權限） |
| `/admin/users` | 使用者管理 |
| `/admin/containers` | 容器管理 |
| `/api/public/files` | 公開檔案列表 |

## API 端點

### 一般 API

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/auth/login` | 登入 |
| POST | `/api/auth/register` | 註冊 |
| GET | `/api/auth/me` | 取得個人資料 |
| GET | `/api/auth/login-history` | 登入記錄 |
| GET | `/api/files` | 檔案列表 |
| POST | `/api/files/upload` | 上傳檔案 |
| DELETE | `/api/files/{id}` | 刪除檔案 |
| GET | `/api/files/{id}/download` | 下載檔案 |
| GET | `/api/public/files` | 公開檔案列表（不需登入） |
| GET | `/api/keys` | API Key 列表 |
| POST | `/api/keys` | 建立 API Key |
| DELETE | `/api/keys/{id}` | 撤銷 API Key |

### 管理員 API

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/admin/dashboard` | 儀表板統計 |
| GET | `/api/admin/users` | 使用者列表 |
| GET | `/api/admin/users/{id}` | 使用者詳情 |
| PUT | `/api/admin/users/{id}` | 更新使用者（配額、啟用） |
| DELETE | `/api/admin/users/{id}` | 刪除使用者 |
| POST | `/api/admin/users/{id}/reset-password` | 重設密碼 |
| GET | `/api/admin/containers` | 容器列表 |
| POST | `/api/admin/containers/{name}/restart` | 重啟容器 |

---

# 測試

```bash
cd k8s
./test.sh
```

---

# 常見問題

**Q: Docker 容器沒有啟動？**
檢查 Docker Desktop 是否執行中，並確認 `box5-server:latest` 映像檔已建置。

**Q: 無法上傳檔案？**
檢查該使用者的配額（預設 10GB），或聯絡管理員調整。

**Q: 本機同步用戶端無法連線？**
確認 Server 已啟動，且帳號密碼正確。

**Q: 公開檔案無法存取？**
確認檔案放在 `sync/public/` 資料夾下，且已同步到 Server。

**Q: 忘記密碼？**
聯絡管理員透過 `/admin/users` 重設密碼。
