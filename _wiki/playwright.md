# Playwright — 瀏覽器自動化測試工具

## 概述

Playwright 是一個由微軟開發的開放原始碼瀏覽器自動化框架，提供統一的 API 來控制 Chromium、Firefox 和 WebKit。它可以用於端對端（E2E）測試、網頁爬蟲、以及瀏覽器自動化操作。

本專案使用 Playwright 來進行 E2E 測試，模擬真實使用者在網站上的操作流程。

## 技術背景

### 從 Selenium 到 Playwright

在 Playwright 之前，Selenium 是瀏覽器自動化的主流選擇。但 Selenium 有幾個缺點：

1. **WebDriver 協定**：透過 HTTP 與瀏覽器通訊，速度較慢
2. **等待機制**：需要手動加入 `time.sleep()` 等待元素載入
3. **限制**：無法操作網路請求、無法設定瀏覽器上下文

Playwright 透過 Chrome DevTools Protocol（CDP）直接與瀏覽器通訊，解決了上述問題。

### 底層協定

```
Selenium:   Client → WebDriver HTTP Server → Browser Driver → Browser
Playwright: Client → CDP/WebSocket → Browser
```

Playwright 直接透過 WebSocket 與瀏覽器通訊，減少了中介層，速度更快、功能更豐富。

## 核心概念

### Browser

Browser 代表一個瀏覽器實體（如 Chromium、Firefox）。Playwright 可以啟動多個瀏覽器實體：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    # ... 使用瀏覽器
    browser.close()
```

### Browser Context

Browser Context 類似「無痕模式（incognito）」中的一個獨立分頁環境。不同的 context 擁有獨立的 Cookie、儲存空間和權限：

```python
context = browser.new_context(
    viewport={"width": 1280, "height": 720},
    storage_state="auth.json"  # 可保存認證狀態
)
page = context.new_page()
```

### Page

Page 對應瀏覽器中的一個分頁（tab），是測試操作的主要對象：

```python
page = context.new_page()
page.goto("http://localhost:3112")
page.fill("input[name='username']", "ccc")
page.fill("input[name='password']", "cccpass")
page.click("button[type='submit']")
```

## 主要功能

### 自動等待（Auto-waiting）

Playwright 在執行操作前會自動等待元素準備就緒：

```python
# 不需要手動等待
page.click("#submit")  # 自動等待元素出現、可見、非 disabled

# 自訂等待條件
page.wait_for_selector(".file-list")
page.wait_for_load_state("networkidle")  # 等待網路請求完成
```

### 網路請求攔截

Playwright 可以攔截與修改網路請求：

```python
def handle_response(response):
    if response.url.endswith("/api/files"):
        data = response.json()
        print(f"Received {len(data)} files")

page.on("response", handle_response)
```

### 螢幕截圖與錄影

```python
# 截圖
page.screenshot(path="screenshot.png", full_page=True)

# 錄影（需要安裝錄製工具）
context = browser.new_context(record_video_dir="videos/")
```

### 跨瀏覽器測試

```python
for browser_type in [p.chromium, p.firefox, p.webkit]:
    browser = browser_type.launch()
    page = browser.new_page()
    page.goto("http://localhost:3112")
    # ... 執行測試
    browser.close()
```

## 測試寫法

### 同步 API（預設）

```python
def test_login(page):
    page.goto("http://localhost:3112/login")
    page.fill("[name='username']", "ccc")
    page.fill("[name='password']", "cccpass")
    page.click("button[type='submit']")
    expect(page).to_have_url("http://localhost:3112/")
```

### 非同步 API

```python
async def test_login_async(page):
    await page.goto("http://localhost:3112/login")
    await page.fill("[name='username']", "ccc")
    await page.fill("[name='password']", "cccpass")
    await page.click("button[type='submit']")
    await expect(page).to_have_url("http://localhost:3112/")
```

### Page Object Model

將頁面抽象為類別，提高測試的可維護性：

```python
class LoginPage:
    def __init__(self, page):
        self.page = page
    
    def goto(self):
        self.page.goto("http://localhost:3112/login")
    
    def login(self, username, password):
        self.page.fill("[name='username']", username)
        self.page.fill("[name='password']", password)
        self.page.click("button[type='submit']")
    
    @property
    def error_message(self):
        return self.page.text_content("h1")

def test_invalid_login(page):
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("invalid", "wrong")
    assert "Login failed" in login_page.error_message
```

## 本專案的 E2E 測試

本專案的 `tests/test_e2e.py` 使用 Playwright 測試以下場景：

### 測試流程

```python
def test_login_and_view_files(page):
    # 1. 開啟登入頁面
    page.goto("http://localhost:3112/login")
    
    # 2. 輸入憑證
    page.fill("[name='username']", "ccc")
    page.fill("[name='password']", "cccpass")
    page.click("button[type='submit']")
    
    # 3. 確認成功登入，看到檔案列表
    expect(page.locator("h1")).to_contain_text("box5")
    
    # 4. 點擊檢視某個檔案
    page.click("text=View")
    
    # 5. 確認檔案內容正確顯示
    expect(page.locator("body")).to_contain_text("Hello")
```

### 安裝 Playwright

```bash
# 安裝 Playwright 核心套件
uv pip install playwright

# 安裝瀏覽器二進位檔
python -m playwright install chromium
```

## 與其他 E2E 框架比較

| 特性 | Playwright | Selenium | Cypress |
|------|-----------|----------|---------|
| 瀏覽器支援 | Chromium, Firefox, WebKit | 所有主流瀏覽器 | 僅 Chromium |
| 執行速度 | 快 | 中等 | 快 |
| 自動等待 | 原生支援 | 需手動設定 | 原生支援 |
| 網路攔截 | 支援 | 有限 | 支援 |
| 多分頁 | 支援 | 支援 | 有限 |
| 行動裝置模擬 | 支援 | 支援 | 有限 |
| 語言 | JS, Python, Java, .NET | 多種 | 僅 JS |
| 可靠度 | 高 | 中等 | 高 |

## 常見操作範例

```python
# 填寫表單
page.fill("input#username", "ccc")
page.select_option("select#role", "admin")
page.check("input#agree")
page.uncheck("input#notify")

# 點擊操作
page.click("button#submit")
page.dblclick(".file-item")
page.hover(".menu-item")

# 鍵盤操作
page.keyboard.press("Enter")
page.keyboard.type("Hello World")

# 等待
page.wait_for_timeout(1000)       # 等待一段時間
page.wait_for_selector(".result")  # 等待元素出現
page.wait_for_function("window.app.ready")  # 等待特定條件

# 驗證
expect(page.locator(".title")).to_have_text("box5")
expect(page.locator(".files")).to_have_count(3)
expect(page).to_have_title("box5 - File List")
```

## 本專案參考

- `tests/test_e2e.py` 包含 Playwright E2E 測試案例
- `install.sh` 在安裝時執行 `playwright install chromium`
- `pyproject.toml` 將 Playwright 宣告為可選相依（`dev` group）
