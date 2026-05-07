from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Server.database import get_db
from Server.auth import verify_password, get_password_hash, create_access_token, verify_token

router = APIRouter()
security = HTTPBearer()

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class User(BaseModel):
    id: int
    username: str
    created_at: str

class FileInfo(BaseModel):
    id: int
    filename: str
    folder: str = ""
    filepath: str
    size: int
    is_public: bool
    created_at: str
    updated_at: str

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    cursor = db.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return {"id": user[0], "username": user[1]}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "uploads")

@router.post("/register", response_model=User)
async def register(user: UserCreate, db=Depends(get_db)):
    existing = db.execute("SELECT id FROM users WHERE username = ?", (user.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    password_hash = get_password_hash(user.password)
    created_at = datetime.now().isoformat()
    cursor = db.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (user.username, password_hash, created_at)
    )
    cursor = db.execute("SELECT max(id) FROM users")
    result = cursor.fetchone()
    user_id = result[0] if result and result[0] is not None else 1
    return {"id": user_id, "username": user.username, "created_at": created_at}

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db=Depends(get_db)):
    cursor = db.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (user.username,))
    row = cursor.fetchone()
    if not row or not verify_password(user.password, row[2]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": row[1]})
    return {"access_token": access_token}

@router.get("/files", response_model=List[FileInfo])
async def list_files(
    folder: str = "",
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.execute(
        "SELECT id, filename, folder, filepath, size, is_public, created_at, updated_at FROM files WHERE id IN (SELECT MAX(id) FROM files WHERE user_id = ? AND folder = ? GROUP BY filename) ORDER BY filename",
        (current_user["id"], folder)
    )
    files = cursor.fetchall()
    return [
        {
            "id": f[0],
            "filename": f[1],
            "folder": f[2],
            "filepath": f[3],
            "size": f[4],
            "is_public": bool(f[5]),
            "created_at": f[6],
            "updated_at": f[7]
        }
        for f in files
    ]

@router.get("/files/history/{filename}")
async def get_file_history(
    filename: str,
    folder: str = "",
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.execute(
        "SELECT id, filename, folder, filepath, size, is_public, created_at, updated_at FROM files WHERE user_id = ? AND folder = ? AND filename = ? ORDER BY updated_at DESC",
        (current_user["id"], folder, filename)
    )
    files = cursor.fetchall()
    return [
        {
            "id": f[0],
            "filename": f[1],
            "folder": f[2],
            "filepath": f[3],
            "size": f[4],
            "is_public": bool(f[5]),
            "created_at": f[6],
            "updated_at": f[7]
        }
        for f in files
    ]

@router.get("/files/subfolders")
async def list_subfolders(
    folder: str = "",
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.execute(
        "SELECT DISTINCT folder FROM files WHERE user_id = ? AND folder != ''",
        (current_user["id"],)
    )
    subfolders = set()
    for row in cursor.fetchall():
        full_folder = row[0]
        if folder == "":
            if "/" in full_folder:
                subfolders.add(full_folder.split("/")[0])
            else:
                subfolders.add(full_folder)
        else:
            prefix = folder + "/"
            if full_folder.startswith(prefix):
                rest = full_folder[len(prefix):]
                if "/" in rest:
                    subfolders.add(rest.split("/")[0])
                else:
                    subfolders.add(rest)
    return {"subfolders": sorted(subfolders)}

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form(""),
    is_public: bool = Form(False),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    user_dir = os.path.join(UPLOAD_DIR, str(current_user["id"]), folder)
    os.makedirs(user_dir, exist_ok=True)
    filepath = os.path.join(user_dir, file.filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size = os.path.getsize(filepath)
    now = datetime.now().isoformat()
    cursor = db.execute(
        "INSERT INTO files (user_id, filename, folder, filepath, size, is_public, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (current_user["id"], file.filename, folder, filepath, size, int(is_public), now, now)
    )
    cursor = db.execute("SELECT max(id) FROM files")
    result = cursor.fetchone()
    file_id = result[0] if result and result[0] is not None else 1
    return {
        "id": file_id,
        "filename": file.filename,
        "folder": folder,
        "filepath": filepath,
        "size": size,
        "is_public": is_public,
        "created_at": now,
        "updated_at": now
    }

@router.get("/files/{file_id}")
async def download_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.execute(
        "SELECT filepath, filename FROM files WHERE id = ? AND user_id = ?",
        (file_id, current_user["id"])
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return {"filepath": row[0], "filename": row[1]}

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.execute(
        "SELECT filepath FROM files WHERE id = ? AND user_id = ?",
        (file_id, current_user["id"])
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    if os.path.exists(row[0]):
        os.remove(row[0])
    db.execute("DELETE FROM files WHERE id = ?", (file_id,))
    return {"message": "File deleted"}

@router.get("/public/files")
async def list_public_files(db=Depends(get_db)):
    cursor = db.execute(
        "SELECT id, filename, filepath, size, created_at FROM files WHERE is_public = 1 ORDER BY updated_at DESC"
    )
    files = cursor.fetchall()
    return [
        {
            "id": f[0],
            "filename": f[1],
            "filepath": f[2],
            "size": f[3],
            "created_at": f[4]
        }
        for f in files
    ]