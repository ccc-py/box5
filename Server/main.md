# Server/main.py — 應用程式入口點

## 背景理論

FastAPI 是一個基於 Python 的非同步 Web 框架，利用 Starlette 與 Pydantic 提供高效能的 API 開發體驗。本檔案作為伺服器的進入點，負責：

- 建立 FastAPI 應用實體
- 設定 CORS 中介軟體，允許跨域請求（Client 與 Website 可能需要跨域存取）
- 在啟動時初始化資料庫（`init_db()`）
- 掛載 `/api` 前綴的所有路由
- 提供檔案編輯器的 HTTP API 端點（`/api/editor/files`、`/api/editor/file`）
- 建立 WebSocket 端點 `/ws/editor` 供即時編輯器與終端機使用
- 提供健康檢查端點 `/health`

其中 CORS（Cross-Origin Resource Sharing）是瀏覽器的安全機制，允許伺服器宣告哪些來源可以存取其資源。`allow_origins=["*"]` 表示允許所有來源，這在開發階段很方便。

WebSocket 是不同於 HTTP 的傳輸協定，建立在 TCP 之上，允許伺服器與客戶端之間進行全雙工（full-duplex）通訊，適合需要即時推送資料的場景，如終端機模擬。
