# xterm.js — 瀏覽器端的終端機模擬器

## 概述

xterm.js 是一個使用 TypeScript 開發的終端機模擬器，完全在瀏覽器中執行。它模擬了傳統終端機（如 xterm、VT100）的行為，讓 Web 應用程式可以提供命令列介面。

本專案的編輯器使用 xterm.js 搭配 WebSocket 與後端的 zsh shell 通訊，實現瀏覽器中的終端機功能。

## 歷史背景

### 實體終端機

VT100 是 DEC（Digital Equipment Corporation）在 1978 年推出的終端機，成為終端機模擬的工業標準。它定義了：
- **逸出序列（Escape Sequences）**：以 `ESC [` 開頭的控制碼，用於控制游標位置、顏色、文字樣式
- **畫面緩衝（Screen Buffer）**：80x24 字元的文字畫面

### 從 xterm 到 xterm.js

- **xterm**：Unix 系統中最早的終端機模擬器，由 XFree86 專案開發
- **xterm.js**：在瀏覽器中重新實作 xterm 的功能，由 SourceLair 開發，現由 Codicode 維護

## 核心功能

### 終端機模擬

xterm.js 模擬了實體終端機的所有行為：

```javascript
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';

// 建立終端機實體
const term = new Terminal({
    cursorBlink: true,        // 游標閃爍
    cursorStyle: 'bar',       // 游標樣式（block、underline、bar）
    fontSize: 14,             // 字型大小
    fontFamily: 'Menlo, monospace',
    theme: {
        background: '#1E1E1E',
        foreground: '#D4D4D4',
        cursor: '#AEAFAD',
        selection: '#264F78'
    },
    rows: 24,                 // 行數
    cols: 80,                 // 列數
    scrollback: 1000          // 回滾行數
});

// 掛載到 DOM
term.open(document.getElementById('terminal-container'));

// 自動調整大小
const fitAddon = new FitAddon();
term.loadAddon(fitAddon);
fitAddon.fit();
```

### 逸出序列處理

終端機最核心的功能是處理逸出序列（Escape Sequences）：

```
ESC [ 3 1 m    → 設定文字顏色為紅色
ESC [ 1 ; 3 2 m → 設定文字為粗體 + 綠色
ESC [ 2 J       → 清除整個畫面
ESC [ H         → 游標回到原點
ESC [ 1 2 A     → 游標上移 12 行
```

xterm.js 內建對所有標準逸出序列的支援，包括：
- **SGR（Select Graphic Rendition）**：文字顏色、粗體、斜體、底線
- **游標控制**：移動、儲存、恢復位置
- **畫面操作**：清除、捲動、插入/刪除行
- **替代畫面緩衝（Alternate Screen Buffer）**：vim、less 等程式切換到另一個畫面

### 附加元件

xterm.js 提供多個附加元件（addons）：

| 附加元件 | 功能 |
|----------|------|
| `xterm-addon-fit` | 自動調整大小填滿容器 |
| `xterm-addon-web-links` | 網址可點擊 |
| `xterm-addon-search` | 文字搜尋 |
| `xterm-addon-unicode11` | Unicode 11 支援 |
| `xterm-addon-webgl` | WebGL 加速渲染 |
| `xterm-addon-serialize` | 序列化終端機內容 |

## 與 WebSocket 的整合

### 基本架構

```
┌─────────────────────────────────────────────────┐
│                   瀏覽器                           │
│  ┌────────────────┐    ┌────────────────────┐   │
│  │   Monaco Editor│    │    xterm.js        │   │
│  └────────────────┘    └─────────┬──────────┘   │
│                                  │               │
│  ┌───────────────────────────────┴───────────┐   │
│  │            WebSocket 客戶端               │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │ WebSocket
┌──────────────────────▼──────────────────────────┐
│                  伺服器                            │
│  ┌────────────────┬────────────────────────────┐ │
│  │WebSocket 伺服器│         PTY zsh shell     │ │
│  └────────────────┴────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 輸入處理

xterm.js 監聽使用者的按鍵輸入，並透過 WebSocket 發送給伺服器：

```javascript
// 接收使用者輸入並發送
term.onData((data) => {
    // data 可能是單一字元、逸出序列（方向鍵）、或貼上的文字
    ws.send(JSON.stringify({
        type: 'terminal_input',
        content: {
            command: data,       // Enter 送出的是一般字串
            raw_data: data,      // 逐字元傳送（用於方向鍵、Tab 等）
            terminal_id: 'default'
        }
    }));
});
```

### 輸出顯示

伺服器透過 WebSocket 將終端機輸出傳送給瀏覽器，xterm.js 直接寫入：

```javascript
// 接收伺服器資料並寫入終端機
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'terminal_output') {
        const output = msg.content.output;
        if (output.stdout) {
            term.write(output.stdout);
        }
    }
};
```

## 視窗大小調整

當瀏覽器視窗大小改變時，需要通知伺服器更新 PTY 的大小，否則輸出可能會錯亂：

```javascript
// 監聽調整大小事件
window.addEventListener('resize', () => {
    fitAddon.fit();
    const dims = { cols: term.cols, rows: term.rows };
    ws.send(JSON.stringify({
        type: 'resize',
        content: dims
    }));
});
```

伺服端需要透過 `ioctl` 設定 PTY 的大小（詳見 [PTY](pty.md) 說明）。

## WebGL 渲染

xterm.js 支援兩種渲染模式：

### Canvas 渲染（預設）

使用 2D Canvas API，相容性最佳，但大量輸出時可能不夠流暢。

### WebGL 渲染

使用 WebGL API，利用 GPU 加速渲染，特別適合大量文字快速輸出的場景（如 `cat largefile.log`）：

```javascript
import { WebglAddon } from 'xterm-addon-webgl';

term.loadAddon(new WebglAddon());
```

## 與其他終端機方案比較

| 方案 | 技術 | 優點 | 缺點 |
|------|------|------|------|
| xterm.js | JavaScript | 純瀏覽器端執行，無需外掛 | 僅終端機模擬 |
| hterm | JavaScript | Chrome OS 內建 | 獨立性較差 |
| PuTTY | 原生應用 | 功能完整 | 需安裝 |
| iTerm2 | 原生應用 | macOS 原生 | 僅 macOS |

## 本專案中的使用

在本專案的 `/editor` 頁面中：

1. 頁面載入時建立 xterm.js 實體與 WebSocket 連線
2. 使用者輸入命令時，xterm.js 觸發 `onData` 事件
3. 命令透過 WebSocket 發送到後端
4. 後端將命令寫入 PTY（zsh shell）
5. zsh 的輸出透過 PTY → WebSocket → xterm.js 顯示在瀏覽器中

### 樣式整合

xterm.js 的樣式與 Monaco Editor 的深色主題整合：

```css
#terminal-container {
    height: 200px;
    padding: 8px;
    background: #1E1E1E;
}

/* xterm.js 深色主題文字 */
.xterm-viewport {
    scrollbar-width: thin;
    scrollbar-color: #424242 #1E1E1E;
}
```
