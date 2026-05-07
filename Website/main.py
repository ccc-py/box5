from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import requests
import markdown

app = FastAPI(title="box5 Website", version="0.1.0")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SCRIPT_DIR, "static")
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:3111")
API_BASE = f"{SERVER_URL}/api"

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, folder: str = ""):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{API_BASE}/files?folder={folder}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 401:
            return RedirectResponse(url="/login")
        files = resp.json()
        subfolders = get_subfolders(token, folder)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "files": files,
            "subfolders": subfolders,
            "current_folder": folder,
            "username": request.cookies.get("username", "User")
        })
    except Exception:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "files": [],
            "subfolders": [],
            "current_folder": folder,
            "username": request.cookies.get("username", "User"),
            "error": "Cannot connect to server"
        })

def get_subfolders(token: str, folder: str):
    try:
        resp = requests.get(f"{API_BASE}/files/subfolders?folder={folder}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            return resp.json().get("subfolders", [])
    except:
        pass
    return []

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        resp = requests.post(f"{API_BASE}/login", json={"username": username, "password": password})
        if resp.status_code != 200:
            return HTMLResponse(content="<h1>Login failed</h1><a href='/login'>Try again</a>", status_code=401)
        token = resp.json()["access_token"]
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="token", value=token)
        response.set_cookie(key="username", value=username)
        return response
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1><a href='/login'>Try again</a>", status_code=500)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("token")
    response.delete_cookie("username")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "register": True})

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    try:
        resp = requests.post(f"{API_BASE}/register", json={"username": username, "password": password})
        if resp.status_code != 200:
            return HTMLResponse(content="<h1>Registration failed</h1><a href='/register'>Try again</a>", status_code=400)
        return RedirectResponse(url="/login", status_code=302)
    except Exception:
        return HTMLResponse(content="<h1>Error</h1><a href='/register'>Try again</a>", status_code=500)

@app.get("/view/{file_id}", response_class=HTMLResponse)
async def view_file(request: Request, file_id: int):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{API_BASE}/files/{file_id}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        file_info = resp.json()
        file_path = file_info["filepath"]
        filename = file_info["filename"]
        ext = os.path.splitext(filename)[1].lower()
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        if ext == ".md":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            html_content = markdown.markdown(content)
            return templates.TemplateResponse("view.html", {
                "request": request,
                "content": html_content,
                "filename": filename,
                "file_type": "markdown"
            })
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return templates.TemplateResponse("view.html", {
                "request": request,
                "content": content,
                "filename": filename,
                "file_type": "text"
            })
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            return templates.TemplateResponse("view.html", {
                "request": request,
                "filename": filename,
                "file_type": "image",
                "filepath": file_path
            })
        else:
            return RedirectResponse(url=f"/download/{file_id}")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/public")
async def public_files(request: Request):
    try:
        resp = requests.get(f"{API_BASE}/public/files")
        files = resp.json()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "files": files,
            "username": "Public",
            "public_view": True
        })
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/download/{file_id}")
async def download_file(request: Request, file_id: int):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{API_BASE}/files/{file_id}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        file_info = resp.json()
        file_path = file_info["filepath"]
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            from fastapi.responses import Response
            return Response(content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={file_info['filename']}"})
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/history/{file_id}", response_class=HTMLResponse)
async def file_history(request: Request, file_id: int):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{API_BASE}/files/{file_id}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        current_file = resp.json()
        filename = current_file["filename"]
        folder = current_file.get("folder", "")
        resp = requests.get(f"{API_BASE}/files/history/{filename}?folder={folder}", headers={"Authorization": f"Bearer {token}"})
        files = resp.json()
        return templates.TemplateResponse("history.html", {
            "request": request,
            "files": files,
            "filename": filename,
            "folder": folder
        })
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/raw{path:path}")
async def raw_file(path: str):
    full_path = path
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            content = f.read()
        ext = os.path.splitext(full_path)[1].lower()
        media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        return Response(content, media_type=media_types.get(ext, "application/octet-stream"))
    raise HTTPException(status_code=404, detail="File not found")