# PTY (Pseudo-Terminal) — 偽終端機

## 概述

PTY（Pseudo-Terminal，偽終端機）是 Unix 系統中的一種裝置對（device pair），用於模擬實體終端機的行為。它由一對檔案描述子（file descriptor）組成：master 端與 slave 端。程式（如終端機模擬器、ssh、tmux）可以透過 PTY 來與其他程式互動，就像它們在實際的終端機中執行一樣。

本專案的編輯器使用 PTY 讓瀏覽器中的 xterm.js 可以與伺服器上的 zsh shell 進行互動。

## 歷史背景

### 實體終端機時代

在早期的電腦系統中，使用者透過實體終端機（如 DEC VT100）來與主機互動。終端機包含鍵盤與顯示器，透過序列埠連接到主機。

```
[使用者] → [鍵盤] → [序列線] → [主機]
                    [序列線] ← [主機] ← [顯示器]
```

### 偽終端機的誕生

隨著圖形化介面的發展，需要在視窗系統中模擬終端機功能。PTY 應運而生，它提供了與實體終端機相同的介面，但完全在軟體中實作。

## PTY 的運作原理

### 架構

```
┌────────────────────────────────────────────┐
│              Application                   │
│  ┌────────┐          ┌──────────────────┐  │
│  │ xterm.js│         │    zsh shell    │  │
│  │ (瀏覽器)│          │   (user process) │  │
│  └────▲───┘          └────────▲─────────┘  │
│       │                      │             │
│  ┌────┴───┐          ┌────────┴─────────┐  │
│  │WebSocket│          │  slave (/dev/pts)│  │
│  └────────┘          └──────────────────┘  │
│       │                      ▲             │
│  ┌────┴──────────────────────┴──────────┐  │
│  │           master 端                   │  │
│  │  (pty.openpty() 回傳的 fd)            │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

### 核心元件

1. **Master 端**：由終端機模擬器（如 xterm.js 的後端）控制，負責讀取 slave 端的輸出，寫入使用者輸入
2. **Slave 端**：連接到 shell 行程（如 zsh），外觀上就像一個實體終端機裝置（`/dev/pts/N`）

### 資料流

```
使用者輸入 "ls\n" →
  xterm.js → WebSocket → master → slave → zsh stdin
                                             ↓
zsh stdout → slave → master → WebSocket → xterm.js →
  使用者看到 "file1.txt\nfile2.txt\n"
```

## 在本專案中的實作

### 建立 PTY

```python
import pty
import os
import subprocess

def start_shell(session_key, cwd):
    # 1. 建立 PTY 對
    master, slave = pty.openpty()
    
    # 2. 啟動 zsh，將 IO 連接到 slave
    proc = subprocess.Popen(
        ['/bin/zsh'],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        start_new_session=True,
        env=os.environ.copy()
    )
    
    # 3. 關閉 slave 端（由子行程使用）
    os.close(slave)
    
    # 4. 儲存 master 端供後續讀寫
    manager.shell_processes[session_key] = {
        'proc': proc,
        'master': master,
        'cwd': cwd
    }
```

### 寫入命令

```python
def handle_terminal_input(client_id, terminal_id, command):
    session_key = f"{client_id}_{terminal_id}"
    shell_info = manager.shell_processes.get(session_key)
    master = shell_info['master']
    
    # 將命令寫入 slave 端，zsh 會收到就像在鍵盤輸入一樣
    os.write(master, (command + '\n').encode('utf-8'))
```

### 讀取輸出

```python
async def read_pty_output_continuous(client_id, terminal_id):
    session_key = f"{client_id}_{terminal_id}"
    
    while True:
        shell_info = manager.shell_processes.get(session_key)
        if not shell_info:
            break
        
        master = shell_info['master']
        
        # 非同步讀取，避免阻塞
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            data = os.read(master, 4096)
            if data:
                text = data.decode('utf-8', errors='replace')
                # 透過 WebSocket 發送給瀏覽器
                await websocket.send_text(text)
```

## select 模組與非阻塞 I/O

### 為什麼需要 select

`os.read(master, 4096)` 是阻塞呼叫，如果沒有資料可讀，它會一直等待。在非同步程式中，這會阻塞整個事件迴圈。

### select 的解決方案

`select.select(rlist, wlist, xlist, timeout)` 可以監控多個檔案描述子，並在它們可讀/可寫/有異常時回傳：

```python
ready, _, _ = select.select([master], [], [], 0.1)  # 等待最多 0.1 秒
if ready:
    data = os.read(master, 4096)  # 確定有資料可讀，不會阻塞
else:
    # 沒有資料可用，繼續其他工作
```

## 終端機的特性

### 行緩衝（Line Buffering）

預設情況下，終端機是「行緩衝（line buffered）」模式。這表示 shell 只有在收到換行字元（`\n`）時才會處理輸入。這就是為什麼本專案在命令後加上 `\n`：

```python
cmd_to_send = command.strip() + '\n'
os.write(master, cmd_to_send.encode('utf-8'))
```

若要實現類似 SSH 那樣的逐字元傳送（如自動完成、方向鍵），需要將終端機設定為「原始模式（raw mode）」：

```python
# 設定終端機為原始模式
import termios
attrs = termios.tcgetattr(master)
attrs[3] = attrs[3] & ~termios.ECHO  # 不顯示輸入
termios.tcsetattr(master, termios.TCSANOW, attrs)
```

### 視窗大小變更

當瀏覽器視窗大小改變時，xterm.js 可以發送視窗大小變更事件。透過 `ioctl` 可以設定 PTY 的視窗大小，讓 shell 知道該如何排列輸出：

```python
import fcntl
import struct

def set_winsize(master, rows, cols):
    # TIOCSWINSZ 控制程式碼
    size = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(master, 0x5413, size)  # 0x5413 = TIOCSWINSZ
```

## PTY vs 其他選項

| 方案 | 優點 | 缺點 |
|------|------|------|
| PTY (本專案) | 完整終端機支援、可執行互動程式 | 實作較複雜 |
| subprocess.PIPE | 簡單 | 僅支援標準 IO、無終端機功能 |
| pexpect | 自動化互動 | 不適合 Web 場景 |
| SSH | 成熟、安全 | 需要 SSH 伺服器設定 |

## 安全性注意事項

1. **PTY 資源洩漏**：每個 PTY 使用兩個檔案描述子，必須確保連線中斷時正確關閉
2. **行程管理**：shell 行程可能變成殭屍行程（zombie），需要確保 `wait()` 被呼叫
3. **權限隔離**：原則上 shell 應該以權限受限的使用者執行，而非本專案使用的 root

本專案的 `ConnectionManager.disconnect()` 會正確清理所有資源：
```python
def disconnect(self, client_id):
    # 關閉 master 檔案描述子
    if shell_info.get('master'):
        os.close(shell_info['master'])
    # 終止 shell 行程
    if shell_info.get('proc'):
        shell_info['proc'].terminate()
        shell_info['proc'].wait()
```
