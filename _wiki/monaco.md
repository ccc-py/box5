# Monaco Editor — 瀏覽器端程式碼編輯器

## 概述

Monaco Editor 是微軟開發的基於 Web 的程式碼編輯器，也是 Visual Studio Code（VS Code）的核心編輯器元件。它完全在瀏覽器中執行，提供了與桌面 IDE 相當的編輯體驗。

本專案的 `/editor` 頁面使用 Monaco Editor 來提供線上的程式碼編輯功能。

## 技術背景

### 從 VS Code 到網頁

VS Code 本身是基於 Electron（瀏覽器核心 + Node.js）的桌面應用程式。Monaco Editor 是 VS Code 編輯器核心的網頁版本，不包含 VS Code 的擴展系統與整合開發環境功能，但保留了核心的編輯能力。

### 核心功能

- **語法高亮（Syntax Highlighting）**：支援超過 100 種程式語言
- **自動完成（Autocompletion）**：基於語言服務（Language Server Protocol）
- **程式碼折疊（Code Folding）**：折疊/展開函式、類別等區塊
- **多游標編輯（Multi-cursor Editing）**：同時編輯多個位置
- **差異比對（Diff Editor）**：並排比較兩個檔案的差異
- **尋找與取代（Find and Replace）**：支援正規表達式
- **錯誤標記（Error Markers）**：即時顯示語法錯誤與警告
- **縮排引導線（Indent Guides）**：視覺化顯示縮排層級

## 在瀏覽器中的使用

### 安裝

```bash
npm install monaco-editor
# 或透過 CDN 載入
```

### 基本使用

```html
<!DOCTYPE html>
<html>
<head>
    <!-- 從 CDN 載入 Monaco Editor -->
    <link rel="stylesheet" data-name="vs/editor/editor.min.css"
          href="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/editor/editor.min.css">
</head>
<body>
    <div id="editor-container" style="height: 600px;"></div>
    
    <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js"></script>
    <script>
        require.config({
            paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
        });
        
        require(['vs/editor/editor.main'], function () {
            // 建立編輯器實體
            const editor = monaco.editor.create(
                document.getElementById('editor-container'),
                {
                    value: '// Hello, box5!\nconsole.log("hello");\n',
                    language: 'javascript',
                    theme: 'vs-dark',
                    automaticLayout: true,
                    minimap: { enabled: true },
                    fontSize: 14,
                    tabSize: 4,
                    wordWrap: 'on'
                }
            );
        });
    </script>
</body>
</html>
```

### 常用設定選項

```javascript
const editor = monaco.editor.create(element, {
    value: '',                    // 初始內容
    language: 'python',           // 語言
    theme: 'vs-dark',             // 主題（vs, vs-dark, hc-black）
    automaticLayout: true,        // 自動調整大小
    minimap: { enabled: true },   // 顯示迷你地圖
    fontSize: 14,                 // 字型大小
    lineNumbers: 'on',            // 行號顯示
    renderWhitespace: 'selection', // 顯示空白字元
    tabSize: 4,                   // Tab 寬度
    wordWrap: 'on',               // 自動換行
    scrollBeyondLastLine: false,  // 禁止滾動超過最後一行
    folding: true,                // 啟用程式碼折疊
    bracketPairColorization: {    // 括號配對著色
        enabled: true
    }
});
```

## 語言服務（Language Services）

### 何謂語言服務

語言服務是一套提供程式語言智慧型功能的系統，包括：
- 自動完成建議
- 語法錯誤檢查
- 定義跳轉（Go to Definition）
- 尋找參考（Find All References）
- 重新命名符號（Rename Symbol）

### 語言服務的模式

1. **內建靜態服務**：Monaco Editor 對某些語言（HTML、CSS、JSON、TypeScript）內建語言服務
2. **透過 WebWorker**：語言服務在背景執行緒中執行，不阻塞 UI
3. **Language Server Protocol (LSP)**：透過 WebSocket 與後端語言伺服器通訊，可支援任何語言

### 本專案中的語言支援

本專案未實作完整的 LSP 整合，但 Monaco Editor 本身支援大量的語言語法高亮與基本編輯功能。

## 與 WebSocket 的結合

在本專案中，Monaco Editor 與 WebSocket 結合提供完整的編輯體驗：

```
編輯器內容變更 → 儲存按鈕 → fetch POST /api/editor/file → 伺服器寫入檔案

檔案選擇 → fetch GET /api/editor/file?path=xxx → 伺服器讀取檔案 → 編輯器載入內容
```

## 多標籤（Tab）編輯

本專案的編輯器支援多檔案同時編輯：

```javascript
const openTabs = {};
let activeTab = null;

async function openFile(path) {
    if (openTabs[path]) {
        // 切換到已開啟的標籤
        editor.setModel(openTabs[path].model);
        activeTab = path;
        return;
    }
    
    // 從伺服器讀取檔案
    const response = await fetch(`/api/editor/file?path=${encodeURIComponent(path)}`);
    const data = await response.json();
    
    // 建立新的編輯器模型
    const model = monaco.editor.createModel(
        data.content,
        data.language,
        path
    );
    
    openTabs[path] = { model, path };
    editor.setModel(model);
    activeTab = path;
}
```

## 主題客製化

### 內建主題

Monaco Editor 提供三個內建主題：
- `vs`：淺色主題
- `vs-dark`：深色主題（本專案使用）
- `hc-black`：高對比黑色主題

### 自訂主題

```javascript
monaco.editor.defineTheme('box5-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
        { token: 'keyword', foreground: '569CD6' },
        { token: 'string', foreground: 'CE9178' },
    ],
    colors: {
        'editor.background': '#1E1E1E',
        'editor.foreground': '#D4D4D4',
        'editor.lineHighlightBackground': '#2A2A2A',
        'editorCursor.foreground': '#AEAFAD',
        'editor.selectionBackground': '#264F78',
    }
});
```

## 與其他編輯器比較

| 編輯器 | 基底技術 | 語言支援 | 擴展性 | 檔案大小 |
|--------|---------|---------|--------|---------|
| Monaco Editor | JavaScript | 豐富（內建） | 有限 | ~5MB |
| CodeMirror 6 | JavaScript | 豐富（模組化） | 極佳 | ~500KB |
| Ace Editor | JavaScript | 豐富 | 良好 | ~1MB |
| CodeJar | JavaScript | 無（自訂） | 極簡 | ~5KB |

### 選擇 Monaco Editor 的原因

本專案選擇 Monaco Editor 而非其他選項的原因：
1. **VS Code 相容**：與 VS Code 相同的編輯器核心，使用者體驗熟悉
2. **深色主題**：內建高品質的深色主題
3. **語言支援廣泛**：內建大量語言的語法高亮，無需額外載入
4. **自動排版**：支援 automaticLayout，適合嵌入在不同尺寸的容器中
