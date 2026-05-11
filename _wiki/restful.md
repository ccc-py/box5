# RESTful API — 具象狀態傳輸

## 概述

REST（Representational State Transfer，具象狀態傳輸）是一種軟體架構風格，由 Roy Fielding 在其 2000 年的博士論文中提出。RESTful API 是遵循 REST 原則的 Web API 設計風格，使用 HTTP 方法來操作資源（resources）。

本專案的 Server 模組提供 RESTful API 供 Client 與 Website 使用。

## 核心原則

### 1. 資源導向（Resource-Oriented）

一切皆為資源（resource），每個資源由一個 URI（統一資源標識符）來識別：

```
/users          ← 使用者集合
/users/42       ← 特定使用者
/files          ← 檔案集合
/files/123      ← 特定檔案
/files/history/foo.txt  ← 特定檔案的歷史版本
```

### 2. HTTP 方法作為操作

| HTTP 方法 | CRUD 對應 | 特性 |
|-----------|----------|------|
| `GET` | Read | 安全（safe），不改變伺服器狀態 |
| `POST` | Create | 非冪等（non-idempotent），每次建立新資源 |
| `PUT` | Update/Replace | 冪等（idempotent），多次執行結果相同 |
| `PATCH` | Partial Update | 部分更新 |
| `DELETE` | Delete | 冪等，刪除資源 |

### 3. 無狀態（Stateless）

每個請求都包含所有必要資訊，伺服器不儲存客戶端狀態。在本專案中：

```http
GET /api/files HTTP/1.1
Authorization: Bearer eyJzdWIiOiJjY2MifQ...  ← 每個請求都帶有 token
```

### 4. 統一介面（Uniform Interface）

資源透過 URI 識別，操作透過 HTTP 方法表達，回應包含資源的表示（representation）。

## API 設計模式

### 集合模式（Collection Pattern）

```
GET    /api/files          ← 列出所有檔案
POST   /api/files/upload   ← 上傳新檔案
GET    /api/files/{id}     ← 取得特定檔案
DELETE /api/files/{id}     ← 刪除特定檔案
```

### 子資源模式（Sub-resource Pattern）

```
GET    /api/files/{id}/history   ← 檔案的版本歷史
GET    /api/files/subfolders     ← 子資料夾列表
GET    /api/files/bypath/{path}  ← 透過路徑取得檔案
```

### 過濾與排序

使用查詢參數（query parameters）來過濾與排序：

```
GET /api/files?folder=public      ← 過濾資料夾
GET /api/files/history/test.txt?folder=doc  ← 過濾歷史版本
```

## 狀態碼

### 成功狀態碼

| 狀態碼 | 意義 | 使用時機 |
|--------|------|----------|
| `200 OK` | 請求成功 | GET、PUT、PATCH |
| `201 Created` | 資源已建立 | POST（註冊、上傳） |
| `204 No Content` | 成功但無回應內容 | DELETE |

### 用戶端錯誤

| 狀態碼 | 意義 | 使用時機 |
|--------|------|----------|
| `400 Bad Request` | 請求格式錯誤 | 缺少必要欄位 |
| `401 Unauthorized` | 未認證 | 缺少或無效的 token |
| `403 Forbidden` | 無權限 | 無權存取資源 |
| `404 Not Found` | 資源不存在 | 檔案或使用者不存在 |
| `409 Conflict` | 資源衝突 | 使用者名稱已存在 |

### 伺服器錯誤

| 狀態碼 | 意義 |
|--------|------|
| `500 Internal Server Error` | 伺服器內部錯誤 |
| `502 Bad Gateway` | 上游伺服器錯誤 |
| `503 Service Unavailable` | 服務暫時不可用 |

## 本專案的 API 設計

### 使用者管理

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/register` | 註冊新使用者 |
| POST | `/api/login` | 登入，回傳 token |

```json
// POST /api/register
{ "username": "ccc", "password": "1234" }

// 回應 201 Created
{ "id": 1, "username": "ccc", "created_at": "2024-01-01T00:00:00" }
```

### 檔案操作

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/files` | 列出使用者檔案 |
| POST | `/api/files/upload` | 上傳檔案（multipart/form-data） |
| GET | `/api/files/{id}` | 取得檔案資訊 |
| DELETE | `/api/files/{id}` | 刪除檔案 |
| GET | `/api/files/history/{filename}` | 取得檔案歷史版本 |
| GET | `/api/files/subfolders` | 列出子資料夾 |
| GET | `/api/files/bypath/{path}` | 透過路徑取得檔案 |

### 公開檔案

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/public/files` | 列出所有公開檔案 |
| GET | `/api/public/files/bypath/{path}` | 透過路徑取得公開檔案 |

## RESTful 設計的最佳實踐

### 命名慣例

- 使用名詞而非動詞：`/files` 而非 `/getFiles`
- 使用複數名詞：`/users` 而非 `/user`
- 使用 kebab-case 或 snake_case：`/file-history` 或 `/file_history`
- 避免版本號在 URI 中（或使用 Accept header）：`/api/v1/files`

### 分頁（Pagination）

當資源數量很大時，應支援分頁：

```http
GET /api/files?page=2&per_page=50

{
  "data": [...],
  "page": 2,
  "per_page": 50,
  "total": 1000,
  "total_pages": 20
}
```

### HATEOAS

Hypermedia as the Engine of Application State，讓 API 回應包含關聯資源的連結：

```json
{
  "id": 123,
  "filename": "test.txt",
  "links": {
    "self": "/api/files/123",
    "download": "/api/files/123/download",
    "history": "/api/files/123/history"
  }
}
```

## 與 GraphQL 的比較

| 特性 | REST | GraphQL |
|------|------|---------|
| 資料取得 | 固定結構（過度/不足獲取） | 客戶端指定所需欄位 |
| 端點數量 | 多個端點 | 單一端點 |
| 版本管理 | URI 或 Header 版本控制 | 內建（透過欄位增減） |
| 快取 | 原生支援 HTTP 快取 | 需自行實作 |
| 複雜度 | 低 | 中高 |
| 適合場景 | CRUD 為主、快取需求高 | 複雜關聯查詢、多種客戶端 |
