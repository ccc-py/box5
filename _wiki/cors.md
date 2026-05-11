# CORS (Cross-Origin Resource Sharing) — 跨來源資源共享

## 概述

CORS（Cross-Origin Resource Sharing）是一種基於 HTTP 標頭的機制，允許伺服器宣告哪些來源（origin）可以存取其資源。這是瀏覽器實作的「同源政策（Same-Origin Policy）」的例外機制。

本專案的 Server 啟用了 CORS 中介軟體，允許 Client 與 Website 跨域存取 API。

## 同源政策（Same-Origin Policy）

### 何謂同源

同源（same-origin）的定義是：協定（protocol）、主機（host）、連接埠（port）三者完全相同。

```
http://example.com/page1.html
http://example.com/page2.html      ← 同源（相同協定、主機、埠號）

http://example.com:8080/page.html   ← 不同源（埠號不同）
https://example.com/page.html       ← 不同源（協定不同）
http://api.example.com/page.html    ← 不同源（主機不同）
```

### 為何需要同源政策

如果沒有同源政策，惡意網站可以：
1. 讀取使用者在其他網站（如銀行）的資料
2. 偽造請求執行操作（如轉帳）
3. 竊取 Cookie 與 session

瀏覽器會阻止跨來源的請求讀取回應內容，但並不會阻止請求本身（如表單提交、圖片載入）。

## CORS 的運作方式

### 簡單請求（Simple Request）

當請求滿足以下條件時，瀏覽器會直接發送請求，並在回應中檢查 CORS 標頭：

- HTTP 方法：GET、HEAD、POST
- 僅包含安全的 Content-Type：text/plain、multipart/form-data、application/x-www-form-urlencoded
- 無自訂標頭

```
請求：
GET /api/files HTTP/1.1
Origin: http://localhost:3112          ← 告知伺服器請求來源

回應：
Access-Control-Allow-Origin: *         ← 允許所有來源
Access-Control-Allow-Credentials: true ← 允許攜帶憑證（Cookie）
```

### 預檢請求（Preflight Request）

當請求包含非簡單要求的條件（如自訂標頭 `Authorization`），瀏覽器會先發送一個 `OPTIONS` 請求來確認伺服器允許：

```
預檢請求：
OPTIONS /api/files/upload HTTP/1.1
Origin: http://localhost:3112
Access-Control-Request-Method: POST          ← 實際要使用的方法
Access-Control-Request-Headers: Authorization ← 實際要使用的標頭

預檢回應：
Access-Control-Allow-Origin: http://localhost:3112
Access-Control-Allow-Methods: GET, POST, DELETE
Access-Control-Allow-Headers: Authorization
Access-Control-Max-Age: 3600                  ← 快取預檢結果 1 小時
```

預檢請求確認通過後，瀏覽器才會發送實際的請求。

## CORS 標頭詳解

### 回應標頭（伺服器 → 瀏覽器）

| 標頭 | 說明 | 範例 |
|------|------|------|
| `Access-Control-Allow-Origin` | 允許的來源 | `*` 或 `http://localhost:3112` |
| `Access-Control-Allow-Methods` | 允許的 HTTP 方法 | `GET, POST, DELETE` |
| `Access-Control-Allow-Headers` | 允許的自訂標頭 | `Authorization, Content-Type` |
| `Access-Control-Allow-Credentials` | 是否允許憑證 | `true` |
| `Access-Control-Max-Age` | 預檢結果的快取時間（秒） | `3600` |
| `Access-Control-Expose-Headers` | 允許瀏覽器存取的標頭 | `X-Custom-Header` |

### 請求標頭（瀏覽器 → 伺服器）

| 標頭 | 說明 | 範例 |
|------|------|------|
| `Origin` | 請求來源 | `http://localhost:3112` |
| `Access-Control-Request-Method` | 預檢請求中宣告的實際方法 | `POST` |
| `Access-Control-Request-Headers` | 預檢請求中宣告的實際標頭 | `Authorization` |

## 本專案的 CORS 設定

在 `Server/main.py` 中：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 允許所有來源
    allow_credentials=True,       # 允許攜帶憑證
    allow_methods=["*"],          # 允許所有 HTTP 方法
    allow_headers=["*"],          # 允許所有自訂標頭
)
```

### 設定解讀

- `allow_origins=["*"]`：允許任何來源存取 API。這在開發階段很方便，但正式部署時應限制為特定的前端 URL
- `allow_credentials=True`：允許請求攜帶憑證（Cookie、Authorization 標頭）。注意：當 `allow_credentials=True` 時，`allow_origins` 不能設為 `*`，必須指定明確的來源
- `allow_methods=["*"]`：允許所有 HTTP 方法（GET、POST、DELETE 等）
- `allow_headers=["*"]`：允許所有自訂標頭

### 為何本專案需要 CORS

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Client     │    │   Server     │    │   Website    │
│ (port 動態)  │    │ (port 3111)  │    │ (port 3112)  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       │  POST /api/files  │                   │
       │  Origin: null     │                   │
       │──────────────────►│                   │
       │                   │                   │
       │  GET /api/files   │                   │
       │  Origin: http://  │                   │
       │  localhost:3112   │                   │
       │◄─────────────────│                   │
```

Client 可能是命令列程式（不經瀏覽器，無 CORS 限制），而 Website 在 port 3112，與 Server 的 port 3111 不同，因此需要 CORS。

## 安全性考量

### 不建議使用 `allow_origins=["*"]`

雖然 `*` 最方便，但在正式環境中應指定明確的來源：

```python
# 正式環境
allow_origins=[
    "https://mywebsite.com",
    "https://api.mywebsite.com"
]
```

### Credentialed requests 的注意事項

當 `allow_credentials=True` 時，`allow_origins` 不能為 `*`：

```python
# 這會出錯
allow_origins=["*"],
allow_credentials=True,

# 必須明確指定
allow_origins=["https://mywebsite.com"],
allow_credentials=True,
```

### 常見的 CORS 錯誤

```
Access to fetch at 'http://localhost:3111/api/files'
from origin 'http://localhost:3112' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

這個錯誤表示伺服器沒有回傳 CORS 標頭，常見原因：
1. 伺服器未設定 CORS 中介軟體
2. 伺服器回應為 5xx 錯誤（不會附加 CORS 標頭）
3. 代理伺服器（如 Nginx）過濾了 OPTIONS 請求

## 與其他解決方案的比較

| 方案 | 機制 | 適用場景 |
|------|------|----------|
| CORS | HTTP 標頭 | 瀏覽器中的跨來源請求 |
| JSONP | `<script>` 標籤 + callback | 僅 GET 請求，舊版瀏覽器 |
| Proxy | 中繼伺服器轉發請求 | 無法修改伺服器設定時 |
| PostMessage | `window.postMessage()` | iframe 間通訊 |

## 本專案參考

- Server 端在 `Server/main.py` 中設定 CORS 中介軟體
- Website 透過 `requests` 函式庫（非瀏覽器）呼叫 Server API，不受 CORS 限制
- Client 透過 `requests` 函式庫（命令列程式）呼叫 Server API，不受 CORS 限制
- 瀏覽器訪問 Website（port 3112）時，若網站 JavaScript 直接呼叫 Server API（port 3111），需要 CORS 支援
