import os
import base64
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire.isoformat()})
    json_str = json.dumps(to_encode)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return encoded

def verify_token(token: str) -> Optional[dict]:
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