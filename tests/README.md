# tests — 測試模組

本目錄包含 box5 專案的所有測試案例，使用 pytest 測試框架。

## 測試類型

| 檔案 | 類型 | 說明 |
|------|------|------|
| `test_server.py` | 單元測試 | 測試 server 認證、資料庫、檔案操作等核心功能 |
| `test_server_api.py` | API 測試 | 透過 TestClient 測試各 API 端點的行為 |
| `test_client.py` | 單元測試 | 測試 client API 封裝與配置 |
| `test_sync.py` | 單元測試 | 測試同步引擎的檔案監控邏輯 |
| `test_website.py` | 單元測試 | 測試網站路由與模板渲染 |
| `test_e2e.py` | E2E 測試 | 使用 Playwright 模擬瀏覽器操作，測試完整流程 |
| `conftest.py` | 測試配置 | pytest 共用的 fixture 與設定 |

## 測試方法論

- **單元測試**：測試個別模組或函式的行為，盡量避免外部依賴
- **API 測試**：使用 FastAPI 的 TestClient 模擬 HTTP 請求，測試 API 端點的回應
- **E2E 測試**：使用 Playwright 自動化瀏覽器，模擬真實使用者操作

## 執行方式

```bash
./test.sh
```

細節請參考專案根目錄的 `test.sh` 與 `AGENTS.md`。
