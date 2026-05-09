import os
import sys
import docker
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import markdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Box5 Docker", version="0.1.0", lifespan=lifespan)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SCRIPT_DIR, "static")
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
UPLOAD_DIR = os.path.join(SCRIPT_DIR, "uploads")
CONTAINER_DIR = os.path.join(SCRIPT_DIR, "containers")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONTAINER_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SERVER_PORT = 3111
BASE_HOST = os.getenv("BOX5_HOST", "localhost")
CONTAINER_IMAGE = os.getenv("BOX5_IMAGE", "box5-server:latest")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def get_container_name(username: str) -> str:
    return f"box5-{username}"


def get_user_port(username: str) -> int:
    return hash(username) % 10000 + 20000


class LoginRequest(BaseModel):
    username: str
    password: str


def create_user_container(username: str, password: str) -> bool:
    container_name = get_container_name(username)
    user_port = get_user_port(username)
    user_dir = os.path.join(UPLOAD_DIR, username)
    container_dir = os.path.join(CONTAINER_DIR, username)

    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(container_dir, exist_ok=True)

    try:
        existing = get_client().containers.get(container_name)
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass
    except Exception:
        pass

    try:
        env_vars = [
            f"USERNAME={username}",
            f"PASSWORD={password}",
            f"PORT={user_port}",
            f"UPLOAD_DIR=/data/uploads/{username}"
        ]

        get_client().containers.run(
            CONTAINER_IMAGE,
            name=container_name,
            detach=True,
            ports={f"{SERVER_PORT}/tcp": user_port},
            environment=env_vars,
            volumes={
                os.path.abspath(UPLOAD_DIR): {"bind": "/data/uploads", "mode": "rw"},
                os.path.abspath(CONTAINER_DIR): {"bind": "/data/containers", "mode": "rw"}
            },
            remove=True,
            network_mode="bridge"
        )
        return True
    except Exception as e:
        print(f"Error creating container: {e}")
        return False


def get_user_server_url(username: str) -> str:
    user_port = get_user_port(username)
    return f"http://{BASE_HOST}:{user_port}"


def get_user_api(username: str) -> str:
    return f"{get_user_server_url(username)}/api"


def stop_user_container(username: str) -> bool:
    container_name = get_container_name(username)
    try:
        container = get_client().containers.get(container_name)
        container.stop(timeout=5)
        return True
    except docker.errors.NotFound:
        return True
    except Exception as e:
        print(f"Error stopping container: {e}")
        return False


def delete_user_container(username: str) -> bool:
    container_name = get_container_name(username)
    try:
        container = get_client().containers.get(container_name)
        container.remove(force=True)
        return True
    except docker.errors.NotFound:
        return True
    except Exception as e:
        print(f"Error deleting container: {e}")
        return False


def check_container_status(username: str) -> str:
    container_name = get_container_name(username)
    try:
        container = get_client().containers.get(container_name)
        return container.status
    except docker.errors.NotFound:
        return "not_found"
    except Exception:
        return "error"


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, folder: str = ""):
    token = request.cookies.get("token")
    username = request.cookies.get("username")
    if not token or not username:
        return RedirectResponse(url="/login")

    try:
        resp = requests.get(f"{get_user_api(username)}/files?folder={folder}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 401:
            return RedirectResponse(url="/login")
        files = resp.json()
        subfolders = get_subfolders(username, token, folder)
        return templates.TemplateResponse(request=request, name="index.html", context={
            "files": files,
            "subfolders": subfolders,
            "current_folder": folder,
            "username": username
        })
    except Exception as e:
        return templates.TemplateResponse(request=request, name="index.html", context={
            "files": [],
            "subfolders": [],
            "current_folder": folder,
            "username": username,
            "error": f"Cannot connect to your container: {e}"
        })


def get_subfolders(username: str, token: str, folder: str):
    try:
        resp = requests.get(f"{get_user_api(username)}/files/subfolders?folder={folder}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("subfolders", [])
    except:
        pass
    return []


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user_dir = os.path.join(UPLOAD_DIR, username)
    token_file = os.path.join(user_dir, ".token")

    if not os.path.exists(token_file):
        return HTMLResponse(content="<h1>User not found</h1><a href='/login'>Try again</a>", status_code=401)

    with open(token_file, "r") as f:
        stored_token = f.read().strip()

    try:
        resp = requests.post(f"{get_user_api(username)}/login", json={"username": username, "password": password}, timeout=5)
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
    return templates.TemplateResponse(request=request, name="login.html", context={"register": True})


@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    user_dir = os.path.join(UPLOAD_DIR, username)
    if os.path.exists(user_dir):
        return HTMLResponse(content="<h1>Username already exists</h1><a href='/register'>Try again</a>", status_code=400)

    os.makedirs(user_dir, exist_ok=True)

    if not create_user_container(username, password):
        os.rmdir(user_dir)
        return HTMLResponse(content="<h1>Failed to create container</h1><a href='/register'>Try again</a>", status_code=500)

    return RedirectResponse(url="/login", status_code=302)


async def fetch_file_info_by_path(username: str, path: str, token: str):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if token:
        try:
            resp = requests.get(f"{get_user_api(username)}/files/bypath/{path}", headers=headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
    try:
        resp = requests.get(f"{get_user_api(username)}/public/files/bypath/{path}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


@app.get("/view/{path:path}")
async def view_file(request: Request, path: str):
    token = request.cookies.get("token")
    username = request.cookies.get("username")

    if not token or not username:
        return RedirectResponse(url="/login")

    file_info = await fetch_file_info_by_path(username, path, token)
    if not file_info and not path.endswith(".html"):
        file_info = await fetch_file_info_by_path(username, f"{path}/index.html" if path else "index.html", token)

    if not file_info:
        if path.isdigit() and token:
            try:
                resp = requests.get(f"{get_user_api(username)}/files/{path}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                if resp.status_code == 200:
                    file_info = resp.json()
            except:
                pass

    if not file_info:
        return HTMLResponse(content="<h1>File not found</h1>", status_code=404)

    file_path = file_info["filepath"]
    filename = file_info["filename"]
    ext = os.path.splitext(filename)[1].lower()

    if not os.path.exists(file_path):
        return HTMLResponse(content="<h1>File not found on disk</h1>", status_code=404)

    if ext == ".md":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        html_content = markdown.markdown(content)
        return templates.TemplateResponse(request=request, name="view.html", context={
            "content": html_content,
            "filename": filename,
            "file_type": "markdown"
        })
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return templates.TemplateResponse(request=request, name="view.html", context={
            "content": content,
            "filename": filename,
            "file_type": "text"
        })
    elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        with open(file_path, "rb") as f:
            content = f.read()
        media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        return Response(content, media_type=media_types.get(ext, "image/jpeg"))
    elif ext in [".html", ".htm", ".css", ".js"]:
        with open(file_path, "rb") as f:
            content = f.read()
        media_types = {".html": "text/html", ".htm": "text/html", ".css": "text/css", ".js": "text/javascript"}
        return Response(content, media_type=media_types.get(ext, "text/plain"))
    else:
        with open(file_path, "rb") as f:
            content = f.read()
        return Response(content, media_type="application/octet-stream")


@app.get("/public")
async def public_files(request: Request):
    return HTMLResponse(content="<h1>Public files not available in container mode</h1>")


@app.get("/download/{file_id}")
async def download_file(request: Request, file_id: int):
    token = request.cookies.get("token")
    username = request.cookies.get("username")
    if not token or not username:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{get_user_api(username)}/files/{file_id}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        file_info = resp.json()
        file_path = file_info["filepath"]
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            return Response(content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={file_info['filename']}"})
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)


@app.get("/history/{file_id}", response_class=HTMLResponse)
async def file_history(request: Request, file_id: int):
    token = request.cookies.get("token")
    username = request.cookies.get("username")
    if not token or not username:
        return RedirectResponse(url="/login")
    try:
        resp = requests.get(f"{get_user_api(username)}/files/{file_id}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        current_file = resp.json()
        filename = current_file["filename"]
        folder = current_file.get("folder", "")
        resp = requests.get(f"{get_user_api(username)}/files/history/{filename}?folder={folder}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        files = resp.json()
        return templates.TemplateResponse(request=request, name="history.html", context={
            "files": files,
            "filename": filename,
            "folder": folder
        })
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)


@app.get("/editor", response_class=HTMLResponse)
async def editor_page(request: Request, path: str = "./sync"):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login")
    user_server = get_user_server_url(username)
    ws_url = user_server.replace("http://", "ws://").replace("https://", "wss://")
    return templates.TemplateResponse(request=request, name="editor.html", context={
        "initial_path": path,
        "server_url": ws_url
    })


@app.get("/status")
async def container_status(request: Request):
    username = request.cookies.get("username")
    if not username:
        return {"status": "not_logged_in"}
    return {"status": check_container_status(username), "username": username}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)