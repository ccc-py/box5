# Server/models.py — 模型匯入層

## 背景理論

本檔案僅作為模組整合層，將 `database.py`、`auth.py`、`routes.py` 中的功能匯出，方便外部模組統一引用。這種模式稱為「匯出門面（Facade）模式」，簡化了 import 路徑。

Pydantic 模型（`UserCreate`、`UserLogin`、`FileInfo` 等）定義在 `routes.py` 中而非獨立檔案，因為這些模型與 API 路由緊密耦合，放在一起便於維護。

資料庫表格定義（schema）則放在 `database.py` 的 `init_db()` 函式中，因為資料表結構屬於資料庫層的職責。
