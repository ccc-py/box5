# JWT (JSON Web Token) — 無狀態認證機制

## 概述

JWT（JSON Web Token，RFC 7519）是一種開放標準（RFC 7519），定義了一種緊湊且自包含（self-contained）的方式，以 JSON 物件的形式在各方之間安全傳輸資訊。JWT 通常用於認證（authentication）與資訊交換。

本專案使用簡化的自製 JWT 機制來管理使用者會話（session），不同於標準的 JWT 實現。

## JWT 的結構

一個 JWT 由三個部分組成，以點（`.`）分隔：

```
xxxxx.yyyyy.zzzzz
├─────┤├─────┤├─────┤
│     ││     ││     │
Header  Payload Signature
```

### Header（標頭）

Header 通常包含 token 的類型與使用的簽章演算法：

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg`：簽章演算法（如 HS256、RS256）
- `typ`：類型，通常為 "JWT"

### Payload（承載）

Payload 包含宣告（claims），即要傳遞的資料。宣告分為三類：

**註冊宣告（Registered Claims）**：
```json
{
  "sub": "user123",       // 主體（subject）
  "iss": "box5-server",   // 發行者（issuer）
  "exp": 1700000000,      // 到期時間（expiration）
  "iat": 1699996400,      // 發行時間（issued at）
  "nbf": 1699996400       // 生效時間（not before）
}
```

**公開宣告（Public Claims）**：可自定義，但建議在 IANA JSON Web Token Registry 註冊或使用 collision-resistant 名稱。

**私有宣告（Private Claims）**：雙方約定的自訂資料：

```json
{
  "sub": "ccc",
  "role": "admin",
  "permissions": ["read", "write", "delete"]
}
```

### Signature（簽章）

簽章用於驗證 token 沒有被篡改。標準 JWT 使用 HMAC-SHA256 演算法：

```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

## 本專案的實作（簡化版）

本專案實作了簡化的 JWT 機制，不包含標準的簽章，僅使用 base64 編碼：

### Token 建立

```python
def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire.isoformat()})
    json_str = json.dumps(to_encode)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return encoded
```

流程：
1. 複製 payload 資料
2. 加入 `exp`（到期時間，ISO 8601 格式）
3. 序列化為 JSON
4. 使用 base64 URL-safe 編碼

### Token 驗證

```python
def verify_token(token: str):
    try:
        json_str = base64.urlsafe_b64decode(token.encode()).decode()
        data = json.loads(json_str)
        exp = datetime.fromisoformat(data.get("exp"))
        if datetime.now(timezone.utc) > exp:
            return None    # 已過期
        return {"sub": data.get("sub")}
    except Exception:
        return None        # 無效的 token
```

流程：
1. base64 解碼
2. JSON 解析
3. 檢查是否過期
4. 回傳使用者資訊

### 與標準 JWT 的差異

| 特性 | 標準 JWT | 本專案實作 |
|------|----------|-----------|
| 簽章 | HMAC-SHA256 或 RSA | 無簽章 |
| 完整性保護 | 有（簽章驗證） | 無（僅 base64 編碼） |
| 機密性 | 無（payload 可解碼） | 無（payload 可解碼） |
| 有效期限 | exp 為 Unix timestamp | exp 為 ISO 8601 字串 |
| 安全性 | 較高 | 較低（無法防篡改） |

### 安全性考量

由於本專案的 token 僅 base64 編碼而無簽章，任何人都可以解碼並修改 payload 內容。這在正式環境中不安全，建議改為標準 JWT 實作：

```python
import hmac
import hashlib
import base64

def create_jwt(payload: dict, secret: str) -> str:
    header = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
    payload_encoded = base64url_encode(json.dumps(payload))
    signature = hmac.new(
        secret.encode(),
        f"{header}.{payload_encoded}".encode(),
        hashlib.sha256
    ).digest()
    return f"{header}.{payload_encoded}.{base64url_encode(signature)}"
```

## 認證流程

```
客戶端（Client/Website）              伺服器（Server）
       │                                  │
       │  POST /api/login                  │
       │  {username, password}             │
       │─────────────────────────────────►│
       │                                   │
       │  驗證密碼                          │
       │  建立 token                       │
       │                                   │
       │  {access_token: "xxx.yyy.zzz"}    │
       │◄─────────────────────────────────│
       │                                   │
       │  儲存 token                       │
       │  （Cookie 或 localStorage）        │
       │                                   │
       │  GET /api/files                   │
       │  Authorization: Bearer xxx...     │
       │─────────────────────────────────►│
       │                                   │
       │  驗證 token                       │
       │  處理請求                          │
       │                                   │
       │  {files: [...]}                   │
       │◄─────────────────────────────────│
```

## Token 儲存方式

### Cookie（本專案使用）

Website 模組將 token 儲存在 HTTP Cookie 中：

```python
response.set_cookie(key="token", value=token)
```

優點：自動隨請求發送，不需要前端程式碼處理。缺點：可能受到 CSRF 攻擊。

### localStorage

Client 模組將 token 儲存在記憶體中（未持久化）：

```python
self.token = data["access_token"]
```

優點：不受 CSRF 影響。缺點：需要手動在每個請求中加入 Authorization 標頭。

## Token 生命週期

### Access Token（存取令牌）

- 短期有效（本專案設為 15~30 分鐘）
- 每次請求時驗證
- 過期後需要重新登入

### Refresh Token（刷新令牌）

本專案未實作 Refresh Token。更完整的實作應包含：

1. **Access Token**：短期（15 分鐘），用於 API 請求
2. **Refresh Token**：長期（7 天），用於取得新的 Access Token
3. **Token Rotation**：每次使用 Refresh Token 時更新它，防止被盜用

## 安全最佳實踐

1. **使用 HTTPS**：防止 token 在傳輸過程中被攔截
2. **設定適當的到期時間**：越短越安全
3. **不要在 payload 中存放敏感資訊**：payload 僅 base64 編碼，非加密
4. **使用標準 JWT 函式庫**：避免自製實作的安全性漏洞
5. **實作 Token 撤銷**：讓使用者可以登出所有裝置
6. **限制 Token 使用範圍**：如綁定 IP 位址或 User-Agent
