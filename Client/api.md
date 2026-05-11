# Client/api.py — API 客戶端

## 背景理論

本檔案封裝了對伺服器 RESTful API 的所有 HTTP 請求，使用 `requests` 函式庫實作。採用「客戶端認證流程（Client Credentials Flow）」模式：

### Token 管理
- 登入成功後將 token 儲存在實體變數 `self.token` 中
- 每次 API 請求時自動帶入 `Authorization: Bearer {token}` 標頭
- 若未登入就呼叫需認證的 API，會拋出 `ValueError`

### API 方法
- `register(username, password)` — 註冊新使用者
- `login(username, password)` — 登入並取得 token
- `upload_file(filepath, folder, is_public)` — 上傳檔案（multipart/form-data）
- `list_files()` — 取得檔案列表
- `download_file(file_id, dest_path)` — 透過檔案 ID 下載
- `delete_file(file_id)` — 刪除檔案

### 錯誤處理
所有 API 方法皆使用 `resp.raise_for_status()` 來檢查 HTTP 狀態碼，若伺服器回傳 4xx 或 5xx 會拋出 `requests.HTTPError`，由呼叫者決定如何處理。
