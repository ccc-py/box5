# FastAPI — 高效能 Python Web 框架

## 概述

FastAPI 是一個現代化的 Python Web 框架，專為建置 API 而設計。它基於 Starlette（非同步網路程式庫）與 Pydantic（資料驗證），提供了與 Node.js 或 Go 相當的高效能，同時保留 Python 的簡潔語法。

本專案的 Server、Website 與 k8s 模組全部使用 FastAPI 建置。

## 背景與設計哲學

### 為何需要另一個 Python Web 框架

在 FastAPI 出現之前，Python 的主流 Web 框架有：

- **Django**：全能型框架，內建 ORM、管理後台等，但較重且非同步支援較晚
- **Flask**：輕量級微框架，靈活但需要自行組合各種套件
- **Tornado**：原生支援非同步，但生態系較小

FastAPI 的目標是結合上述框架的優點：非同步效能、自動 API 文件、型別安全、以及良好的開發體驗。

### 關鍵技術

FastAPI 的核心建立在兩個強大的函式庫之上：

1. **Starlette**：輕量級的非同步 Web 框架工具包，處理路由、中介軟體、WebSocket 等底層網路操作
2. **Pydantic**：基於 Python 型別提示（type hints）的資料驗證函式庫

## 核心特性

### 非同步原生（Async Native）

FastAPI 支援 Python 的 `async/await` 語法，允許在處理 I/O 密集型操作（如資料庫查詢、HTTP 請求、檔案讀寫）時不阻塞事件迴圈：

```python
@app.get("/files")
async def list_files():
    # 非等待（non-blocking）的資料庫查詢
    files = await db.fetch_all()
    return files
```

非同步的優點在於：當一個請求在等待 I/O 時，伺服器可以處理其他請求，大幅提升並發能力。

### 自動 API 文件

FastAPI 會根據路由定義與 Pydantic 模型自動產生兩份 API 文件：

- **Swagger UI**（`/docs`）：互動式 API 測試介面
- **ReDoc**（`/redoc`）：更美觀的 API 參考文件

這在開發階段非常有用，不需要花時間手動維護 API 文件。

### 型別安全

透過 Python 的型別提示（type hints），FastAPI 可以自動：

1. 驗證請求資料的型別與格式
2. 進行資料轉換（如將 JSON 字串轉為 Python 物件）
3. 在編輯器中提供自動完成與型別檢查

```python
@app.post("/items")
async def create_item(item: Item):  # Item 是 Pydantic 模型
    return item
```

## 路由系統

### 路徑裝飾器

FastAPI 使用裝飾器（decorator）來定義路由：

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

路徑參數（`{user_id}`）會自動傳遞給函式參數，且可指定型別來啟用自動驗證。

### 路由前綴（APIRouter）

當專案規模變大時，可以使用 `APIRouter` 來組織路由：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/files")
async def list_files():
    ...

# 在主程式中掛載
app.include_router(router)
```

本專案的 `Server/routes.py` 使用這種方式將所有 API 路由集中在一個檔案中，然後在 `Server/main.py` 中掛載。

### 依賴注入（Dependency Injection）

FastAPI 的依賴注入系統允許將共享的邏輯（如資料庫連線、認證檢查）提取為可重複使用的函式：

```python
async def get_db():
    db = sql5.connect(...)
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
async def get_users(db=Depends(get_db)):
    cursor = db.execute("SELECT * FROM users")
    return cursor.fetchall()
```

本專案廣泛使用依賴注入來取得資料庫連線與驗證使用者身分。

## 中介軟體（Middleware）

中介軟體是處理每個請求/回應的鉤子（hook），可以在請求到達路由之前或回應發送之後執行邏輯：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

本專案使用 CORS 中介軟體來允許跨域請求。

## WebSocket 支援

FastAPI 原生支援 WebSocket：

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

本專案的編輯器功能就是透過 WebSocket 來實現即時終端機模擬。

## Pydantic 模型

Pydantic 負責資料驗證與序列化：

```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class FileInfo(BaseModel):
    id: int
    filename: str
    folder: str = ""
    size: int
    is_public: bool
    created_at: str
```

- 請求資料會自動驗證並轉換為對應的 Python 型別
- 回應資料會自動序列化為 JSON
- 可設定預設值、可選欄位、欄位驗證規則

## 本專案中的應用

### Server 模組（port 3111）

使用 FastAPI 提供 RESTful API，包含使用者管理與檔案操作。使用 sql5 資料庫與自製 JWT 認證。

### Website 模組（port 3112）

使用 FastAPI + Jinja2 模板來渲染 HTML 頁面。不同於傳統的 SPA（Single Page Application），採用伺服器端渲染（SSR）方式。

### k8s 模組（port 8000）

使用 FastAPI 提供 Web UI 與 API，同時管理 Docker 容器的生命週期。

## 效能比較

| 框架 | 效能（每秒請求數） | 非同步支援 | 自動文件 | 生態系 |
|------|------------------|-----------|---------|--------|
| FastAPI | ~50,000 req/s | 原生 | 有 | 中等 |
| Flask | ~10,000 req/s | 外掛 | 無 | 豐富 |
| Django | ~5,000 req/s | 部分（3.1+） | 無 | 豐富 |
| Node.js Express | ~60,000 req/s | 原生 | 無 | 豐富 |

（以上數據為粗略估計，實際效能取決於應用場景與硬體）
