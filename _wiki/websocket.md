# WebSocket — 全雙工即時通訊協定

## 概述

WebSocket 是一種在單一 TCP 連線上提供全雙工（full-duplex）通訊的協定，定義於 RFC 6455。它讓伺服器可以主動向客戶端推送資料，而不需要客戶端不斷輪詢（polling）。WebSocket 特別適合需要即時雙向資料交換的應用，如聊天軟體、即時遊戲、協作編輯器與終端機模擬。

本專案的編輯器使用 WebSocket 來實現瀏覽器中的終端機模擬（xterm.js ↔ zsh）。

## HTTP 的局限性

### 傳統的 HTTP 請求-回應模型

HTTP 是「請求-回應（request-response）」模型，客戶端發送請求，伺服器回傳回應。這種模型的問題：

- **伺服器無法主動推送**：伺服器無法在沒有請求的情況下發送資料給客戶端
- **輪詢（Polling）浪費資源**：客戶端必須不斷發送請求來檢查是否有新資料
- **每個請求都有開銷**：HTTP 標頭在每次請求中都會重複傳送

### 解決方案演進

```
Polling:     C →→→ S    C →→→ S    C →→→ S    (浪費頻寬)
Long Poll:  C →→→ S →→→ C →→→ S →→→ C  (改善，但仍非即時)
WebSocket:  C ↔↔↔↔↔↔↔↔↔↔↔↔ S          (真正的即時)
```

## 連線建立

WebSocket 連線透過 HTTP Upgrade 機制建立：

### 握手（Handshake）

```
客戶端請求：
GET /ws/editor HTTP/1.1
Host: localhost:3111
Upgrade: websocket                 ← 要求升級協定
Connection: Upgrade                ← 標記為升級連線
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==  ← 隨機產生的 base64 金鑰
Sec-WebSocket-Version: 13          ← 協定版本

伺服器回應：
HTTP/1.1 101 Switching Protocols   ← 同意升級
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=  ← 驗證用的回應值
```

握手完成後，連線從 HTTP 協定切換為 WebSocket 協定，雙方可以開始雙向傳送資料。

## 資料框架

WebSocket 的資料以「框架（frame）」為單位傳送：

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |                               |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                Extended payload length continued               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                    Payload Data (application data)             |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 欄位說明

- **FIN**（1 bit）：是否為最後一個框架
- **RSV**（3 bits）：保留位，用於擴展
- **opcode**（4 bits）：框架類型
  - `0x0`：續傳框架
  - `0x1`：文字框架（UTF-8）
  - `0x2`：二進位框架
  - `0x8`：關閉連線
  - `0x9`：Ping
  - `0xA`：Pong
- **MASK**（1 bit）：客戶端發送的資料必須遮罩（masking）
- **Payload Length**（7/16/64 bits）：資料長度
- **Masking Key**（4 bytes）：若 MASK=1，用於遮罩資料

### 為什麼客戶端必須遮罩

這是一個安全機制。WebSocket 設計者擔心攻擊者可以利用快取 poisoning 攻擊，透過惡意的 WebSocket 連線污染 HTTP 快取。遮罩確保攻擊者無法控制實際傳送的 bytes。

## 連線維持

### Ping/Pong 心跳

WebSocket 協定內建心跳機制：
- 任一方可發送 Ping 框架
- 接收方必須回覆 Pong 框架
- 若長時間未收到 Pong，可視為連線中斷

許多 Web 伺服器（如 Nginx）有預設的逾時設定（通常 60 秒），若超過時間沒有資料傳送，會主動關閉 WebSocket 連線。

### 關閉連線

任一方可發送 Close 框架（opcode 0x8）來關閉連線，可附帶一個狀態碼與說明文字：

| 狀態碼 | 意義 |
|--------|------|
| 1000 | 正常關閉 |
| 1001 | 離開（如頁面關閉） |
| 1002 | 協定錯誤 |
| 1003 | 不支援的資料型別 |
| 1009 | 訊息過大 |
| 1011 | 伺服器內部錯誤 |

## WebSocket 在 FastAPI 中的實作

FastAPI 原生支援 WebSocket：

```python
@app.websocket("/ws/editor")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()        # 接受握手
    try:
        while True:
            data = await websocket.receive_text()   # 接收文字訊息
            response = handle_message(data)
            await websocket.send_text(response)     # 發送文字訊息
    except WebSocketDisconnect:
        cleanup(websocket)
```

### 本專案的 WebSocket 訊息格式

使用 XML 格式封裝：

```xml
<!-- 終端機輸入 -->
<message type="terminal_input">
    <command>ls -la</command>
    <terminal_id>default</terminal_id>
</message>

<!-- 檔案讀取 -->
<message type="file_read">
    <path>/home/user/test.py</path>
</message>

<!-- 終端機輸出 -->
<message type="terminal_output">
    <output>{"stdout": "file1.txt\nfile2.txt\n", "code": 0}</output>
</message>
```

### 訊息型別

| 型別 | 方向 | 說明 |
|------|------|------|
| `terminal_input` | 客戶端 → 伺服器 | 使用者輸入的命令 |
| `terminal_output` | 伺服器 → 客戶端 | 終端機執行結果 |
| `file_read` | 客戶端 → 伺服器 | 請求讀取檔案 |
| `file_content` | 伺服器 → 客戶端 | 檔案內容 |
| `file_write` | 客戶端 → 伺服器 | 請求寫入檔案 |
| `file_write_result` | 伺服器 → 客戶端 | 寫入結果 |
| `file_list` | 客戶端 → 伺服器 | 請求列出目錄 |
| `file_list_result` | 伺服器 → 客戶端 | 目錄列表 |

## WebSocket vs SSE vs HTTP/2 Server Push

| 特性 | WebSocket | SSE (Server-Sent Events) | HTTP/2 Server Push |
|------|-----------|--------------------------|-------------------|
| 方向 | 全雙工 | 單向（伺服器→客戶端） | 單向（伺服器→客戶端） |
| 協定 | WS/WSS | HTTP | HTTP/2 |
| 資料型別 | 文字 + 二進位 | 僅文字 | 二進位 |
| 瀏覽器支援 | 所有現代瀏覽器 | 大部分（不含 IE） | 有限 |
| 自動重連 | 需自行實作 | 原生支援 | 需自行實作 |
| 適合場景 | 即時雙向通訊 | 伺服器通知/推播 | 資源預載 |

## 安全性考量

### WSS（WebSocket Secure）

與 HTTPS 對應，WSS 是加密的 WebSocket 連線（透過 TLS）。在正式環境中，應始終使用 WSS 而非 WS。

### 跨站 WebSocket Hijacking

攻擊者可以在惡意網站上建立 WebSocket 連線到受害者的伺服器。防禦方法：

1. 驗證 `Origin` 標頭
2. 在 WebSocket 握手時檢查 token（類似 HTTP 的認證）
3. 使用 CSRF token

本專案中，WebSocket 端點未實作認證檢查（僅在編輯器 HTTP API 中檢查 token），這在正式環境中需要加強。

## 本專案參考

- `Server/editor_ws.py` — WebSocket 編輯器後端，處理終端機與檔案操作
- `Server/main.py` — 註冊 WebSocket 端點 `/ws/editor`
- 瀏覽器端使用 JavaScript 的 `WebSocket` API 連線到伺服器
- xterm.js 作為終端機介面，透過 WebSocket 與伺服器的 zsh shell 通訊
