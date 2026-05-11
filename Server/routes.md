# Server/routes.py — API 路由層

## 背景理論

REST（Representational State Transfer）是一種軟體架構風格，使用 HTTP 方法（GET、POST、DELETE 等）來操作資源。本檔案定義了所有公開的 API 端點：

### 認證路由
- `POST /api/register` — 使用者註冊，密碼經 SHA256 雜湊後存入資料庫
- `POST /api/login` — 使用者登入，驗證密碼後回傳 base64 編碼的 access token

### 檔案路由
- `GET /api/files` — 列出使用者的檔案，支援 folder 參數過濾，並做基於檔名（filename）的去重複（deduplication）
- `GET /api/files/subfolders` — 列出使用者的子資料夾
- `POST /api/files/upload` — 上傳檔案，支援 folder 與 is_public 參數
- `GET /api/files/{file_id}` — 下載檔案（回傳實體路徑）
- `DELETE /api/files/{file_id}` — 刪除檔案（同時刪除磁碟檔案與資料庫紀錄）
- `GET /api/files/history/{filename}` — 取得某檔案的所有歷史版本
- `GET /api/files/bypath/{path}` — 透過路徑路徑取得檔案

### 公開檔案路由
- `GET /api/public/files` — 列出所有公開檔案
- `GET /api/public/files/bypath/{path}` — 透過路徑取得公開檔案

### 去重複機制

由於 Client 端監控資料夾時可能重複上傳相同檔案，伺服器在列表時會根據 `filename` 欄位去重複（保留最新版本），確保使用者看到不重複的檔案列表。這是透過 `seen` 集合與排序來實作的。
