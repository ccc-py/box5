# Client/config.py — 設定管理

## 背景理論

設定（configuration）管理是應用程式中不可或缺的一環。本檔案使用環境變數（environment variables）作為設定來源，遵循「12-Factor App」的建議：

- `SERVER_URL` — 伺服器位址（預設：http://localhost:3111）
- `SYNC_FOLDER` — 本機同步資料夾路徑（預設：./sync_folder）
- `USERNAME` / `PASSWORD` — 預設的使用者憑證

### 為何使用環境變數
- 與程式碼分離，不同環境（開發/測試/正式）可使用不同設定
- 不將敏感資訊（如密碼）寫死在程式碼中
- 符合 Docker 等容器化部署的最佳實踐
