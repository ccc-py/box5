# Watchdog — Python 檔案系統事件監控函式庫

## 概述

Watchdog 是一個 Python 函式庫，用於監控檔案系統的變動事件（新增、修改、刪除、移動）。它基於各平台的原生通知機制（如 Linux 的 inotify、macOS 的 FSEvents、Windows 的 ReadDirectoryChangesW），而非輪詢（polling）機制，因此效率更高。

本專案的 Client 使用 watchdog 來監控同步資料夾的變動，實現即時檔案同步。

## 觀察者模式（Observer Pattern）

Watchdog 的核心架構基於「觀察者模式（Observer Pattern）」：

### 模式結構

```
┌─────────────┐    事件通知    ┌─────────────────────┐
│   Subject    │ ──────────► │    Observer          │
│  (Observer)  │             │ (FileSystemEventHandler)│
│              │             │                      │
│  - schedule()│             │  + on_created()      │
│  - start()   │             │  + on_modified()     │
│  - stop()    │             │  + on_deleted()      │
└─────────────┘             │  + on_moved()        │
                            └─────────────────────┘
```

### 觀察者模式的優點

1. **鬆散耦合**：Subject 與 Observer 之間僅透過事件介面互動
2. **支援多個觀察者**：同一 Subject 可通知多個 Observer
3. **動態新增/移除**：可在執行時動態加入或移除觀察者

## 核心類別

### Observer

`Observer` 是觀察者模式中的 Subject，負責啟動背景執行緒來監控檔案系統：

```python
from watchdog.observers import Observer

observer = Observer()
observer.schedule(event_handler, path, recursive=True)
observer.start()
```

參數說明：
- `event_handler`：處理事件的 `FileSystemEventHandler` 實體
- `path`：要監控的目錄路徑
- `recursive`：是否遞迴監控子目錄

Observer 的內部運作：
1. 啟動一個背景執行緒
2. 該執行緒呼叫平台特定的檔案系統監控 API
3. 當事件發生時，建立對應的 `FileSystemEvent` 物件
4. 將事件傳遞給註冊的 EventHandler

### FileSystemEventHandler

`FileSystemEventHandler` 是觀察者模式中的 Observer，定義了事件處理方法：

```python
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        """檔案或目錄被建立時呼叫"""
        print(f"Created: {event.src_path}")

    def on_modified(self, event):
        """檔案或目錄被修改時呼叫"""
        print(f"Modified: {event.src_path}")

    def on_deleted(self, event):
        """檔案或目錄被刪除時呼叫"""
        print(f"Deleted: {event.src_path}")

    def on_moved(self, event):
        """檔案或目錄被移動時呼叫"""
        print(f"Moved: {event.src_path} -> {event.dest_path}")
```

### FileSystemEvent

`FileSystemEvent` 封裝了事件資訊：

```python
event.src_path   # 事件來源路徑（字串）
event.dest_path  # 目標路徑（僅 on_moved 有此屬性）
event.is_directory  # 是否為目錄事件（布林值）
event.event_type    # 事件類型字串："created", "modified", "deleted", "moved"
```

## 平台實作

Watchdog 針對不同作業系統使用不同的監控機制：

| 平台 | 模組 | 底層技術 | 特性 |
|------|------|----------|------|
| Linux | `inotify` | inotify (Linux kernel 2.6.13+) | 穩定、高效 |
| macOS | `fsevents` | FSEvents (macOS 10.5+) | 高效、但可能合併事件 |
| Windows | `read_directory_changes` | ReadDirectoryChangesW | 穩定 |
| 跨平台 | `polling` | 輪詢（每 200ms 檢查） | 相容性最高、效率最低 |

Watchdog 會自動選擇最適合當前平台的實作。如果無法使用原生機制（如遠端檔案系統），可以強制使用輪詢模式：

```python
from watchdog.observers.polling import PollingObserver

observer = PollingObserver()  # 使用輪詢模式
```

## 事件合併

檔案系統事件在短時間內可能觸發多次。例如，編輯器儲存檔案時可能會觸發多次 `on_modified` 事件。Watchdog 的事件合併行為取決於平台：

- **macOS FSEvents**：會合併短時間內的多次修改事件
- **Linux inotify**：每個寫入操作都會觸發事件，可能需要自行去重

### 本專案的去重策略

本專案的 `SyncHandler` 使用 MD5 雜湊去重：

```python
def on_modified(self, event):
    current_hash = self._get_file_hash(event.src_path)
    old_hash = self.file_hashes.get(event.src_path)
    if current_hash != old_hash:
        # 只有雜湊值不同時才上傳
        self.api.upload_file(event.src_path, ...)
        self.file_hashes[event.src_path] = current_hash
```

## 常見問題

### 事件遺失

在某些情況下（如大量檔案操作），部分事件可能遺失。解決方法：

1. 使用更可靠的平台（Linux inotify 的緩衝區較大）
2. 定期執行完整掃描（類似本專案的 `initial_sync`）
3. 增加事件佇列大小

### 事件重複

一個檔案操作可能觸發多個事件。例如，編輯器儲存檔案可能是「刪除舊檔案 → 建立新檔案」或多次寫入。解決方案：

1. 加入去抖動（debounce）機制：短時間內忽略同檔案的重複事件
2. 使用雜湊比對實際內容是否有變化

### 監控超過目錄數量的限制

Linux 的 inotify 有 watch 數量限制（可透過 `/proc/sys/fs/inotify/max_user_watches` 調整）。如果監控的目錄太多，需要提高這個限制。

## 本專案的實作（Client/sync.py）

```python
class FolderWatcher:
    def __init__(self, api_client, sync_folder):
        self.api = api_client
        self.sync_folder = sync_folder
        self.observer = None
        self.handler = SyncHandler(api_client, sync_folder)

    def start(self):
        os.makedirs(self.sync_folder, exist_ok=True)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.sync_folder, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def initial_sync(self):
        # 啟動時先完整掃描一次，上傳所有檔案
        for root, dirs, files in os.walk(self.sync_folder):
            for filename in files:
                self.api.upload_file(...)
```

### SyncHandler 的事件處理流程

```
檔案新增 (on_created):
  1. 確認是檔案（非目錄）
  2. 確認需要同步（非隱藏檔）
  3. 等待 0.5 秒（確保檔案寫入完成）
  4. 上傳到伺服器
  5. 記錄 MD5 雜湊

檔案修改 (on_modified):
  1. 計算當前 MD5 雜湊
  2. 比對之前記錄的雜湊
  3. 若不同則上傳

檔案刪除 (on_deleted):
  1. 從雜湊快取中移除

檔案移動 (on_moved):
  1. 更新雜湊快取中的路徑
```
