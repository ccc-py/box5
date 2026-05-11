# Server — 雲端伺服器模組

本目錄實作 box5 的後端伺服器，基於 FastAPI 框架與 sql5 資料庫，提供檔案儲存、使用者管理與 WebSocket 編輯器功能。

## 模組說明

| 檔案 | 用途 |
|------|------|
| `main.py` | FastAPI 應用程式進入點，掛載路由中介軟體與 WebSocket |
| `routes.py` | RESTful API 路由，處理使用者註冊/登入/檔案 CRUD |
| `auth.py` | 認證機制，實作 base64 編碼的 JWT token 與 SHA256 密碼雜湊 |
| `models.py` | 模型匯入匯出，整合 database/auth/routes |
| `database.py` | sql5 資料庫連線管理，透過 WebSocket 傳輸協定連線 |
| `editor_ws.py` | WebSocket 編輯器後端，含終端機模擬與檔案操作 |
