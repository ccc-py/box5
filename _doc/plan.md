# box5 專案規劃

## 專案目標
做一個類似 Dropbox 的應用，包含：
- **Client**：桌面客戶端，監控資料夾並同步檔案
- **Server**：雲端伺服器，儲存檔案與使用者資料
- **Website**：網頁介面，讓使用者登入帳號、瀏覽雲端檔案
- markdown (.md) 可以被 render 呈現
- public/ 資料夾下的檔案 （包含 .md)，會直接在網站上公開

## 使用技術

使用 python + fastapi + sql5 實作

* sql5 -- https://pypi.org/project/sql5/
    * 在 /Users/Shared/ccc/project/sql5 有專案原始碼
    * 如果發現 sql5 有任何錯誤或不好用，可以直接修改該原始碼，我是作者，改完我會重新發佈到 pypi
    * 修改完 sql5 記得用 cargo test , pytest, test.sh 重新測試
    * sql5 請用 websocket 模式，才能有持久性。（ 一般 server 模式，每個 connect 都是獨立的 process)

## 系統架構

```
┌─────────────┐     HTTP/HTTPS     ┌─────────────┐
│   Client    │ ◄──────────────►  │   Server    │
│  (桌面程式)  │                    │  (雲端服務)  │
└─────────────┘                    └─────────────┘
       │                                  │
       │                                  ▼
       │                          ┌─────────────┐
       │                          │  Database   │
       │                          └─────────────┘
       │                                  │
       ▼                                  ▼
┌─────────────┐                   ┌─────────────┐
│ Local Files │                   │  Website    │
│  (同步資料夾) │                   │  (網頁介面)  │
└─────────────┘                   └─────────────┘
```

## 核心功能

### Client
- 監控本機資料夾變動（新增、修改、刪除檔案）
- 檔案上傳到 Server
- 即時同步：新增、修改、刪除都自動反映到 Server

# 陳鍾誠的寫程式專屬 skill

1. 必須要寫詳細的單元測試，還有系統測試
    * 如果是網站，必須對 server api 測試，還要使用 Playwright 對網站進行 e2e 測試。
2. 測試框架
    * python 使用 pytest
    * rust 使用 cargo test
    * 必須寫一個 test.sh 做專案測試
3. 程式規範
    * 必須經過 lint 格式檢查與自動格式化（python 使用 ruff）
    * 程式超過 1000 行，就要分成兩個檔案模組。
4. 規劃寫在 _doc/ 下，每一個版本都要寫出 vx.y.md 
    * 例如： v0.1.md v0.2.md ....v 1.1.md
    * 每次進版基本上都前進 0.1 版
5. 語法必須修改到沒有 warning 
    * 如果是 rust ，可以用 #![allow(dead_code, unused)]
    * 如果是 C 必須改到沒 warning.
