# Website/main.py — 網站應用程式

## 背景理論

本檔案實作 box5 的 Web UI，作為 Server API 的前端代理（proxy），透過 HTTP 請求與 Server 通訊。

### 伺服器端渲染（SSR）
不同於現代前端框架（React、Vue）的客戶端渲染，本專案使用伺服器端渲染（Server-Side Rendering），透過 Jinja2 模板引擎在伺服器端產生 HTML 後傳送給瀏覽器。優點是：
- 不需要前後端分離的 API 設計
- 對 SEO 友善（雖然本專案非公開網站）
- 實作簡單，適合小型專案

### 認證流程
- 登入後將 token 存入 Cookie（`response.set_cookie`）
- 每次請求從 Cookie 讀取 token
- token 過期時重新導向到登入頁面

### 路由說明
- `GET /` — 首頁，顯示使用者的檔案列表，支援 folder 參數
- `GET /login` / `POST /login` — 登入頁面
- `GET /logout` — 登出，清除 Cookie
- `GET /register` / `POST /register` — 註冊頁面
- `GET /view/{path}` — 檔案檢視器，根據副檔名決定渲染方式
- `GET /download/{file_id}` — 強制下載檔案
- `GET /history/{file_id}` — 顯示檔案版本歷史
- `GET /public` — 公開檔案頁面
- `GET /editor` — 線上程式碼編輯器

### 檔案類型處理
`/view/{path}` 會根據副檔名採取不同處理：
- `.md` — 使用 Python `markdown` 函式庫渲染為 HTML
- `.txt` — 以純文字顯示在 `<pre>` 區塊
- `.jpg/.png/.gif/.webp` — 直接以原始二進位內容回應，設定正確的 Content-Type
- `.html/.css/.js` — 以原始內容回應，瀏覽器會自動渲染
- 其他 — 以 `application/octet-stream` 回應，觸發下載

### 與 Server 的關係
Website 本身不直接操作資料庫，所有資料都是透過 HTTP 請求向 Server（預設 port 3111）取得。這是一種代理架構，Website 扮演「無狀態（stateless）」的前端角色。
