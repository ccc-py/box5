# Server/auth.py — 認證機制

## 背景理論

認證（Authentication）是確認使用者身分的過程。本專案採用簡化的自製 JWT（JSON Web Token）機制：

### Token 結構
不同於標準 JWT 使用 HMAC-SHA256 簽章，本專案使用 base64 編碼的 JSON 字串，包含：
- `sub` (subject) — 使用者名稱
- `exp` (expiration) — 過期時間

### 編碼流程
1. 將 payload（dict）複製一份
2. 加入 `exp` 欄位（ISO 8601 格式的過期時間）
3. 序列化為 JSON 字串
4. 用 base64 URL-safe 編碼

### 驗證流程
1. base64 解碼
2. JSON 解析
3. 比對 `exp` 是否已過期

### 密碼儲存
使用 SHA256 雜湊（hash）來儲存密碼。雖然實務上建議使用 bcrypt 或 argon2 等慢速雜湊函數，但本專案為簡化實作採用 SHA256。

### 安全性考量
- `SECRET_KEY` 可透過環境變數設定，否則隨機產生
- Token 時效為 30 分鐘（`ACCESS_TOKEN_EXPIRE_MINUTES`）
- 每次請求透過 `HTTPBearer` 來驗證 token
