# Client/main.py — 客戶端進入點

## 背景理論

本檔案是桌面同步客戶端的啟動程式，負責解析使用者提供的命令列參數，初始化 API 客戶端，然後啟動資料夾監控。

### 命令列參數
使用 Python 標準的 `argparse` 模組解析：
- `--server` — 伺服器 URL，預設從環境變數 `SERVER_URL` 讀取
- `--folder` — 要同步的本機資料夾路徑
- `--username` / `--password` — 使用者憑證

### 啟動流程
1. 建立 `ApiClient` 實體
2. 嘗試註冊使用者（若已存在則忽略）
3. 登入取得 access token
4. 建立 `FolderWatcher` 進行初始同步
5. 進入主迴圈，持續監控檔案變動
6. 收到 KeyboardInterrupt（Ctrl+C）時優雅關閉

### 優雅關閉
當使用者按下 Ctrl+C 中斷程式時，Python 會拋出 `KeyboardInterrupt` 例外。捕捉此例外後呼叫 `watcher.stop()` 來停止檔案監控執行緒，確保資料一致性。
