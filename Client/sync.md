# Client/sync.py — 資料夾同步引擎

## 背景理論

本檔案實作檔案同步的核心邏輯，使用 `watchdog` 函式庫監控檔案系統變動。

### 觀察者模式（Observer Pattern）
watchdog 採用觀察者模式（Observer Pattern）：
- `Observer` — 主體（subject），負責監控檔案系統事件
- `FileSystemEventHandler` — 觀察者（observer），定義事件處理邏輯
- 當檔案系統發生變動時，Observer 會通知 EventHandler

### SyncHandler
繼承 `FileSystemEventHandler`，處理四種事件：
- `on_created` — 檔案新增：延遲 0.5 秒後上傳，確保檔案寫入完成
- `on_modified` — 檔案修改：比對 MD5 雜湊值，避免重複上傳
- `on_deleted` — 檔案刪除：清除本機雜湊快取
- `on_moved` — 檔案移動：更新本機雜湊快取

### MD5 雜湊去重
透過 MD5 雜湊比對來避免重複上傳：
1. 檔案修改事件觸發時，計算當前的 MD5 雜湊
2. 與上次記錄的雜湊比對
3. 只有雜湊不同時才上傳

### 公開檔案辨識
若檔案位於 `sync/public/` 目錄下，會被標記為公開檔案（`is_public=True`），伺服器會允許未登入的使用者存取。

### FolderWatcher
- `initial_sync()` — 程式啟動時掃描整個資料夾，將所有檔案上傳
- `start()` — 啟動 watchdog 觀察者，開始監控檔案變動
- `stop()` — 停止觀察者，等待執行緒結束
