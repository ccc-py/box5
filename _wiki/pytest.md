# pytest — Python 單元測試框架

## 概述

pytest 是一個成熟且功能完整的 Python 測試框架，支援簡單的單元測試到複雜的功能測試。它以其簡潔的語法、強大的 fixture 系統和豐富的外掛生態系聞名。

本專案使用 pytest 來執行所有的測試案例（單元測試、API 測試、E2E 測試）。

## 設計理念

### 簡單至上

pytest 的設計哲學是讓測試程式碼盡可能簡單。與 unittest（Python 標準函式庫）不同，pytest 不需要類別繼承或特殊的方法命名約定：

```python
# unittest 的寫法
import unittest
class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

# pytest 的寫法（更簡潔）
def test_add():
    assert 1 + 1 == 2
```

### assert 重寫

pytest 會重寫 Python 的 `assert` 語句，提供更詳細的失敗訊息：

```
# 普通 assert 失敗時
>       assert 1 + 1 == 3
E       assert (1 + 1) == 3
E        +  where 1 + 1 = 2
```

無需像 unittest 那樣使用 `self.assertEqual()`、`self.assertIn()` 等專門的 assertion 方法。

## Fixture 系統

Fixture 是 pytest 最強大的功能之一。它讓測試之間的共享資源（如資料庫連線、HTTP 客戶端）可以透過依賴注入的方式使用：

### 基本 Fixture

```python
import pytest

@pytest.fixture
def db_connection():
    # 設定（setup）
    db = sql5.connect(...)
    yield db
    # 清理（teardown）
    db.close()

def test_query(db_connection):
    result = db_connection.execute("SELECT 1")
    assert result is not None
```

在測試函式中宣告參數名稱 `db_connection`，pytest 會自動尋找同名的 fixture 並注入。

### Fixture 的作用域

```python
@pytest.fixture(scope="function")   # 每個測試函式執行一次（預設）
@pytest.fixture(scope="class")      # 每個測試類別執行一次
@pytest.fixture(scope="module")     # 每個測試模組執行一次
@pytest.fixture(scope="session")    # 整個測試階段執行一次
```

選擇適合的 scope 可以大幅提升測試效能。例如，資料庫初始化使用 `session` scope，只需執行一次。

### 內建 Fixture

pytest 提供多個內建 fixture：

```python
def test_tmp_path(tmp_path):
    # tmp_path 是一個暫時目錄的路徑
    file = tmp_path / "test.txt"
    file.write_text("hello")
    assert file.read_text() == "hello"

def test_capsys(capsys):
    # 捕捉 stdout/stderr 輸出
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

## conftest.py

`conftest.py` 是 pytest 的設定檔，可以定義 fixture、外掛和鉤子（hooks）。pytest 會自動載入各目錄下的 conftest.py：

```
tests/
├── conftest.py        ← 全局設定與 fixture
├── test_server.py
├── test_client.py
└── test_e2e.py
```

本專案的 `tests/conftest.py` 定義了測試用的 fixture（如應用程式實體、資料庫初始化等）。

## 參數化測試

使用 `@pytest.mark.parametrize` 來測試多組輸入：

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
])
def test_double(input, expected):
    assert input * 2 == expected
```

這比在測試函式內寫迴圈更好，因為每個測試案例獨立執行，失敗時可以清楚知道是哪組輸入出了問題。

## 標記（Mark）

pytest 的標記系統可以對測試進行分類：

```python
@pytest.mark.slow
def test_heavy_computation():
    ...

@pytest.mark.skip(reason="功能尚未實作")
def test_future_feature():
    ...

@pytest.mark.skipif(sys.version_info < (3, 10), reason="需要 Python 3.10+")
def test_new_feature():
    ...

@pytest.mark.xfail(reason="已知問題")
def test_known_bug():
    ...
```

### 執行特定標記的測試

```bash
pytest -m slow              # 只執行標記為 slow 的測試
pytest -m "not slow"        # 跳過標記為 slow 的測試
pytest -m "api or e2e"      # 執行 api 或 e2e 標記的測試
```

## Monkeypatching

`monkeypatch` fixture 可以在測試中安全地修改物件或環境變數：

```python
def test_api_client(monkeypatch):
    # 偽造 requests.post 的回應
    def mock_post(url, json=None):
        class MockResponse:
            def json(self):
                return {"access_token": "fake_token"}
            def raise_for_status(self):
                pass
        return MockResponse()
    
    monkeypatch.setattr(requests, "post", mock_post)
    
    client = ApiClient("http://fake-server")
    token = client.login("user", "pass")
    assert token == "fake_token"
```

## 臨時目錄（tmp_path）

pytest 為每個測試函式建立獨立的暫時目錄，並在測試結束後自動清理：

```python
def test_file_upload(tmp_path):
    # 建立暫時檔案
    file = tmp_path / "test.txt"
    file.write_text("hello world")
    
    # 測試上傳
    result = api.upload_file(str(file))
    assert result["success"]
```

## 本專案的測試架構

### 測試檔案組織

| 檔案 | 類型 | 內容 |
|------|------|------|
| `test_server.py` | 單元測試 | 測試認證、資料庫、檔案操作等 |
| `test_server_api.py` | API 測試 | 使用 TestClient 測試 API 端點 |
| `test_client.py` | 單元測試 | 測試 API 客戶端封裝 |
| `test_sync.py` | 單元測試 | 測試檔案同步邏輯 |
| `test_website.py` | 單元測試 | 測試網站路由 |
| `test_e2e.py` | E2E 測試 | Playwright 瀏覽器自動化測試 |

### 執行方式

```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_server.py -v

# 執行 API 測試
pytest tests/test_server_api.py -v

# 執行 E2E 測試
pytest tests/test_e2e.py -v

# 顯示詳細輸出
pytest -v

# 在測試失敗時進入除錯器
pytest --pdb
```

## 與其他測試框架比較

| 框架 | 語法 | Fixture | 參數化 | 外掛 | 學習曲線 |
|------|------|---------|--------|------|---------|
| pytest | 簡潔 | 強大 | 原生支援 | 豐富 | 低 |
| unittest | 冗長（需 extends） | 有限（setUp/tearDown） | 需第三方 | 有限 | 低 |
| nose2 | 類似 pytest | 有 | 有 | 中等 | 中 |
| doctest | 文件內嵌 | 無 | 無 | 無 | 低 |

## 本專案參考

- 所有測試定義在 `tests/` 目錄下
- `tests/conftest.py` 定義共用 fixture
- `test.sh` 使用 pytest 執行所有測試
- `pyproject.toml` 中宣告 `pytest>=7.4.0` 與 `pytest-asyncio>=0.21.0` 相依
