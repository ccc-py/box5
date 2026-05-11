# Pydantic — Python 資料驗證與設定管理

## 概述

Pydantic 是一個 Python 函式庫，利用 Python 的型別提示（type hints）來進行資料驗證與序列化。它為 FastAPI 提供了請求資料的自動驗證與解析能力。

本專案在多個 API 端點中使用 Pydantic 模型來定義請求與回應的資料結構。

## 設計理念

Pydantic 的設計建立在以下核心原則上：

1. **型別安全（Type Safety）**：利用 Python 3.6+ 的型別提示來明確宣告資料結構
2. **自動驗證（Automatic Validation）**：在模型初始化時自動驗證所有欄位
3. **JSON 支援**：原生支援 JSON 序列化與反序列化
4. **效能**：核心使用 Rust 的 pyo3 實作（Pydantic V2 起），效能大幅提升

## 基本用法

### 定義模型

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class FileInfo(BaseModel):
    id: int
    filename: str
    folder: str = ""          # 預設值
    filepath: str
    size: int
    is_public: bool
    created_at: str
    updated_at: str
```

### 自動驗證

```python
# 自動型別轉換
user = UserCreate(username="ccc", password="1234")
# 自動驗證成功

# 型別錯誤會拋出 ValidationError
user = UserCreate(username="ccc", password=1234)
# TypeError: 1234 is not a string (密碼必須是字串)

# 遺漏必要欄位
user = UserCreate(username="ccc")
# ValidationError: password field required
```

### 可選欄位與預設值

```python
class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None   # 可選欄位
    role: str = "user"            # 預設值
    created_at: Optional[datetime] = None

# 只需提供必要欄位
user = User(id=1, username="ccc")
# user.role 自動為 "user"
# user.email 自動為 None
```

## Pydantic V2 新特性

本專案使用 Pydantic V2（`pydantic>=2.0.0`），主要改進：

### Rust 核心

Pydantic V2 將核心驗證邏輯用 Rust 重新實作（使用 pyo3 綁定），驗證速度提升 5~50 倍。

### 新的驗證機制

V2 引入了 `field_validator` 與 `model_validator`：

```python
from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):
    username: str
    password: str
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v
```

### 設定管理

Pydantic 也可以用來管理應用程式設定：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    server_url: str = "http://localhost:3111"
    db_path: str = "box5.db"
    secret_key: str = "default-secret"
    
    class Config:
        env_prefix = "BOX5_"  # 環境變數前綴

settings = Settings()
# 自動從環境變數 BOX5_SERVER_URL, BOX5_DB_PATH 等讀取
```

## 在 FastAPI 中的應用

### 請求驗證

```python
@app.post("/register", response_model=User)
async def register(user: UserCreate, db=Depends(get_db)):
    # FastAPI 自動：
    # 1. 從請求 body 讀取 JSON
    # 2. 使用 UserCreate 模型驗證資料
    # 3. 轉換為 UserCreate 實體
    # 4. 傳遞給函式
    
    # 若驗證失敗，自動回傳 422 Unprocessable Entity
    existing = db.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    ...
    return {"id": 1, "username": user.username, "created_at": "..."}
```

### 回應模型

```python
@app.get("/files", response_model=List[FileInfo])
async def list_files(...):
    # FastAPI 自動：
    # 1. 將回傳值轉換為 List[FileInfo]
    # 2. 過濾不在 FileInfo 中的欄位
    # 3. 自動型別轉換（如 int(is_public) → bool）
    files = cursor.fetchall()
    return [
        {
            "id": f[0],
            "filename": f[1],
            "is_public": bool(f[5]),  # 資料庫的 INTEGER → bool
            ...
        }
    ]
```

## 資料驗證流程

```
客戶端請求 JSON
    │
    ▼
FastAPI 從 request body 讀取 JSON
    │
    ▼
Pydantic 模型驗證：
    ├── 欄位是否存在
    ├── 型別是否正確
    ├── 自訂驗證器（若有）
    └── 預設值填入
    │
    ├── 成功 → 建立 Pydantic 實體
    └── 失敗 → 回傳 422 Validation Error
    │
    ▼
將 Pydantic 實體傳遞給路由函式
```

## 序列化與反序列化

### model_dump() (V2) / dict() (V1)

將模型轉換為字典：

```python
user = UserCreate(username="ccc", password="1234")
data = user.model_dump()
# {"username": "ccc", "password": "1234"}
```

### model_dump_json() (V2) / json() (V1)

直接轉換為 JSON 字串：

```python
user = UserCreate(username="ccc", password="1234")
json_str = user.model_dump_json()
# '{"username": "ccc", "password": "1234"}'
```

## 本專案中的使用

本專案在 `Server/routes.py` 中定義了以下 Pydantic 模型：

| 模型 | 用途 | 欄位 |
|------|------|------|
| `UserCreate` | 註冊請求 | username, password |
| `UserLogin` | 登入請求 | username, password |
| `Token` | 登入回應 | access_token, token_type="bearer" |
| `User` | 使用者資訊 | id, username, created_at |
| `FileInfo` | 檔案資訊 | id, filename, folder, filepath, size, is_public, created_at, updated_at |

## 與其他方案比較

| 方案 | 型別提示整合 | 效能 | 序列化 | FastAPI 整合 |
|------|------------|------|--------|-------------|
| Pydantic V2 | 原生 | 極快（Rust） | 完整 | 原生 |
| Pydantic V1 | 原生 | 快（Python） | 完整 | 原生 |
| attrs/cattrs | 良好 | 快 | 需額外設定 | 無 |
| dataclasses | 良好 | 快 | 無 | 有限 |
| marshmallow | 無（獨立 schema） | 中等 | 完整 | 需整合 |
