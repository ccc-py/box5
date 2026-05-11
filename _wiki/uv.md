# uv — Python 專案與套件管理工具

## 概述

uv 是一個用 Rust 撰寫的高速 Python 套件與專案管理工具，由 Astral（同時也是 Ruff 的開發團隊）開發。它旨在取代 pip、pip-tools、pipx、poetry、pyenv、virtualenv 等傳統工具，提供一個統一的解決方案。

本專案使用 uv 來管理 Python 相依套件與虛擬環境。

## 背景：Python 套件管理的混亂

傳統的 Python 套件管理存在多個工具導致的碎片化問題：

```
pip          → 安裝套件
virtualenv   → 隔離環境
pip-tools    → 鎖定版本
poetry       → 專案管理 + 套件管理
pyenv        → Python 版本管理
pipx         → 全局安裝應用
```

這些工具各自解決部分問題，但整合起來複雜且效率低落。uv 的目標是「統一取代上述所有工具」。

## 核心功能

### 1. 套件安裝

uv 可以完全取代 pip：

```bash
uv pip install flask      # 等同 pip install flask
uv pip install -r requirements.txt  # 從 requirements.txt 安裝
```

uv 的安裝速度比 pip 快 10~100 倍，因為：
- **Rust 實作**：無 Python 直譯器啟動開銷
- **全域快取**：所有專案共享套件快取，不需重複下載
- **並行下載**：同時下載多個套件
- **先進的解析演算法**：更快的依賴解析

### 2. 虛擬環境管理

```bash
uv venv                # 建立 .venv 虛擬環境
uv venv myenv          # 建立自訂名稱的虛擬環境
uv venv --python 3.12  # 指定 Python 版本
```

與 `python -m venv` 不同，uv 會自動下載並快取所需的 Python 版本。

### 3. 專案管理

uv 透過 `pyproject.toml` 來管理專案：

```bash
uv init              # 初始化新專案
uv add fastapi       # 新增相依套件
uv remove requests   # 移除相依套件
uv sync              # 同步鎖定檔案中的套件
uv lock              # 產生/更新鎖定檔案
```

### 4. Python 版本管理

```bash
uv python install 3.12     # 下載並安裝 Python 3.12
uv python install 3.11     # 可同時安裝多個版本
uv python list             # 列出已安裝的版本
uv python pin 3.12         # 設定專案使用的 Python 版本
```

這取代了 `pyenv` 的功能。

### 5. 工具執行

```bash
uv run pytest              # 在專案環境中執行指令
uv tool install ruff       # 全局安裝工具（取代 pipx）
uv tool run black file.py  # 直接執行工具
```

## uv.lock 鎖定檔案

當執行 `uv lock` 或 `uv sync` 時，uv 會產生一個 `uv.lock` 檔案，類似於 `package-lock.json`（npm）或 `Cargo.lock`（Rust）：

```yaml
# uv.lock 的內容結構
version: 1
requires-python: ">=3.10"

[[package]]
name = "fastapi"
version = "0.109.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "starlette" },
    { name = "pydantic" },
]

[[package]]
name = "starlette"
version = "0.36.0"
source = { registry = "https://pypi.org/simple" }
```

lock 檔案確保所有開發者與部署環境使用完全相同的套件版本，避免「在我的機器上可以執行」的問題。

## 相依套件宣告

在 `pyproject.toml` 中宣告相依：

```toml
[project]
name = "box5"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "python-multipart>=0.0.6",
    "requests>=2.31.0",
    "watchdog>=4.0.0",
    "markdown>=3.5.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "playwright>=1.40.0",
]
```

- `dependencies`：執行時必要的套件
- `optional-dependencies`：開發時（如測試）才需要的套件

## 本專案中的 uv 使用

### 安裝

```bash
# install.sh
uv sync                           # 根據 pyproject.toml 安裝所有相依
uv pip install jinja2             # 安裝額外套件
uv pip install websocket-client   # 安裝額外套件
```

### 執行測試

```bash
# test.sh
VENV_PYTHON="$HOME/.venv/bin/python"
$VENV_PYTHON -m pytest tests/...
```

注意：本專案的 test.sh 使用 `$HOME/.venv/bin/python`（顯式指定虛擬環境路徑），而非 `uv run python`，因為要確保取消設定 `VIRTUAL_ENV` 環境變數。

## 與其他工具比較

| 功能 | uv | pip | poetry | pipenv |
|------|-----|-----|--------|--------|
| 套件安裝 | 極快 | 慢 | 中等 | 慢 |
| 虛擬環境 | 內建 | 需 venv | 內建 | 內建 |
| 鎖定檔案 | uv.lock | 無（需 pip-tools） | poetry.lock | Pipfile.lock |
| pyproject.toml | 支援 | 部分 | 原生 | 不支援 |
| Python 版本管理 | 內建 | 無 | 無 | 無 |
| 語言 | Rust | Python | Python | Python |
| 發布套件 | 進行中 | 支援 | 支援 | 不支援 |

## 常見指令速查

```bash
uv sync                 # 安裝所有相依（等同 npm install）
uv add package_name     # 新增相依套件
uv remove package_name  # 移除相依套件
uv lock                 # 更新鎖定檔案
uv run command          # 在專案環境中執行指令
uv pip list             # 列出已安裝套件
uv pip install -r requirements.txt  # 從 requirements.txt 安裝
uv venv                 # 建立虛擬環境
uv cache clean          # 清理快取
uv tool run ruff check  # 執行工具
```

## 本專案參考

- `pyproject.toml` 定義了專案的相依套件
- `uv.lock` 鎖定了所有套件的確切版本
- `install.sh` 使用 `uv sync` 安裝相依
- 開發流程：修改 `pyproject.toml` → `uv lock` → `uv sync`
