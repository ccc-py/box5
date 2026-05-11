import os
import base64
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

# Token 有效期（分鐘），過期後需要重新登入
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# 若環境變數未設定 SECRET_KEY，則隨機產生一組 32 位元組的十六進位金鑰
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"

def get_password_hash(password: str) -> str:
    """將密碼透過 SHA256 雜湊函數轉換為不可逆的字串儲存"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """比對使用者輸入的明碼與資料庫儲存的雜湊值是否一致"""
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """建立 base64 編碼的存取令牌（Access Token），內含使用者名稱與到期時間"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire.isoformat()})
    json_str = json.dumps(to_encode)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return encoded

def verify_token(token: str) -> Optional[dict]:
    """解碼並驗證令牌是否過期，若有效則回傳使用者資訊"""
    try:
        json_str = base64.urlsafe_b64decode(token.encode()).decode()
        data = json.loads(json_str)
        exp_str = data.get("exp", "1970-01-01T00:00:00+00:00")
        exp = datetime.fromisoformat(exp_str).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return None
        return {"sub": data.get("sub")}
    except Exception:
        return None