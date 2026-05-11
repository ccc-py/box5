# Server/editor_ws.py — WebSocket 編輯器後端

## 背景理論

WebSocket 是一種在單一 TCP 連線上提供全雙工通訊的協定，適合需要即時雙向資料交換的應用場景。本檔案實作編輯器的 WebSocket 後端，包含三個核心功能：

### 連線管理（ConnectionManager）
管理所有 WebSocket 連線與對應的 shell 行程（process）。每個客戶端連線時會建立一個 `ConnectionManager` 實體，維護：
- `active_connections` — 活躍連線字典
- `shell_processes` — 每個連線對應的終端機行程

### 訊息協定
使用 XML 格式封裝訊息，每則訊息包含 `type` 屬性與子元素內容：
- `terminal_input` — 使用者輸入的命令
- `terminal_output` — 終端機輸出結果
- `file_read` — 讀取檔案請求
- `file_write` — 寫入檔案請求
- `file_list` — 列出目錄請求

### 終端機模擬（PTY）
透過 Unix 的 pseudo-terminal（PTY）來模擬終端機：
1. `pty.openpty()` 建立一對 master/slave 檔案描述子
2. 啟動 zsh shell 行程，將其 stdin/stdout/stderr 連接到 slave
3. master 端用來讀寫終端機資料
4. `select.select()` 非同步監控 master 是否有可讀資料

這種方式讓瀏覽器中的 xterm.js 可以透過 WebSocket 與伺服器上的 zsh shell 進行互動，就像在本地終端機操作一樣。

### 檔案操作
- `handle_file_read(path)` — 讀取檔案內容，自動偵測語言類型（透過副檔名對應）
- `handle_file_write(path, content)` — 寫入檔案內容，自動建立父目錄
- `handle_file_list(path)` — 列出目錄內容，目錄排在前面，再依名稱排序
