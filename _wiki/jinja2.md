# Jinja2 — Python 模板引擎

## 概述

Jinja2 是一個功能強大的 Python 模板引擎（template engine），由 Armin Ronacher（同時也是 Flask 的作者）開發。它讓開發者可以在 HTML 檔案中嵌入動態內容，實現伺服器端渲染（Server-Side Rendering, SSR）。

本專案的 Website 與 k8s 模組使用 Jinja2 搭配 FastAPI 來渲染 HTML 頁面。

## 模板引擎的原理

模板引擎的核心概念是「分離關注點（Separation of Concerns）」：

```
模板檔案（.html）＋ 資料（context）＝ 最終 HTML

{{ title }}
└─ 模板 ─┘   └─── 資料 ───┘   └─── 最終 HTML ───┘
"My Page"     {"title": "My Page"}   "My Page"
```

### 為何需要模板引擎

- **動態內容**：根據不同使用者顯示不同的資料
- **程式碼重用**：透過模板繼承（template inheritance）共用頁面佈局
- **可維護性**：將 HTML 結構與 Python 邏輯分離

## 模板語法

### 變數（Variables）

使用雙大括號輸出變數值：

```html
<h1>Welcome, {{ username }}!</h1>
<h2>Your email: {{ user.email }}</h2>
```

Jinja2 支援屬性存取（點號）與字典存取（中括號）。

### 過濾器（Filters）

使用 `|` 符號對變數進行轉換：

```html
<p>{{ description|truncate(100) }}</p>   <!-- 截斷字串 -->
<p>{{ content|markdown }}</p>             <!-- Markdown 轉 HTML -->
<p>{{ files|length }} files total</p>     <!-- 取得列表長度 -->
<p>{{ created_at|date("Y-m-d") }}</p>     <!-- 日期格式化 -->
```

### 控制結構（Control Structures）

```html
<!-- 條件判斷 -->
{% if error %}
    <div class="error">{{ error }}</div>
{% endif %}

<!-- 迴圈 -->
<ul>
{% for file in files %}
    <li>{{ file.filename }} ({{ file.size }} bytes)</li>
{% else %}
    <li>No files found</li>
{% endfor %}
</ul>
```

### 模板繼承（Template Inheritance）

模板繼承是 Jinja2 最強大的功能之一，允許定義基礎佈局：

**base.html**：
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}box5{% endblock %}</title>
    <link rel="stylesheet" href="/static/box5.css">
</head>
<body>
    <header>
        {% block header %}
        <h1>box5</h1>
        {% endblock %}
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

**index.html**（繼承 base.html）：
```html
{% extends "base.html" %}

{% block title %}box5 - File List{% endblock %}

{% block content %}
    <h2>Your Files</h2>
    {% for file in files %}
        <div>{{ file.filename }}</div>
    {% endfor %}
{% endblock %}
```

### 引入（Include）

將其他模板內容引入當前模板：

```html
{% include "breadcrumb.html" %}
```

## 在 FastAPI 中使用 Jinja2

### 設定

```python
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="static"), name="static")

# 設定模板目錄
templates = Jinja2Templates(directory="templates")
```

### 渲染模板

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, folder: str = ""):
    files = get_files(folder)
    return templates.TemplateResponse(
        request=request,           # 必須傳入 request
        name="index.html",         # 模板檔案名稱
        context={                  # 傳遞給模板的資料
            "files": files,
            "current_folder": folder,
            "username": "ccc"
        }
    )
```

### 為什麼需要 Request

FastAPI 的 `Jinja2Templates` 需要 `request` 物件來：
1. 產生 URL（透過 `url_for`）
2. 設定 CSRF token
3. 存取使用者會話

## 本專案中的模板

本專案的 Website 模板位於 `Website/templates/`：

### index.html

顯示檔案列表與子資料夾：

```html
{% for file in files %}
    <div class="file-item">
        <span class="filename">{{ file.filename }}</span>
        <span class="filesize">{{ file.size }} bytes</span>
        <a href="/view/{{ file.id }}">View</a>
        <a href="/download/{{ file.id }}">Download</a>
        <a href="/history/{{ file.id }}">History</a>
    </div>
{% endfor %}
```

### login.html

登入與註冊表單：

```html
<form method="POST" action="/login">
    <input type="text" name="username" placeholder="Username">
    <input type="password" name="password" placeholder="Password">
    <button type="submit">Login</button>
</form>
```

### view.html

檔案檢視器，根據檔案類型顯示 Markdown、純文字或程式碼。

### editor.html

線上程式碼編輯器，包含 Monaco Editor 與 xterm.js 終端機。

## 效能考量

### 模板快取

Jinja2 預設會快取編譯後的模板，在生產環境中效能良好。在開發模式中可關閉快取以便即時看到修改：

```python
templates = Jinja2Templates(
    directory="templates",
    auto_reload=True  # 開發模式自動重新載入
)
```

### 與前端框架的選擇

本專案選擇 Jinja2 + SSR 而非 React/Vue 的原因：

| 考量 | Jinja2 (SSR) | React/Vue (CSR) |
|------|-------------|-----------------|
| 開發速度 | 快（無需前後端分離） | 慢（需要 API 設計） |
| SEO | 原生支援 | 需要額外處理 |
| 互動性 | 有限（需要 JavaScript） | 豐富 |
| 複雜度 | 低 | 高 |
| 適合場景 | 內容網站、小型應用 | 複雜互動、大型應用 |
