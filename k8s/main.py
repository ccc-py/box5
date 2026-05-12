import os
import sys
import docker
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import markdown

import auth
import admin as admin_module
import multi as multi_mode
from database_sqlite import get_db, init_db
import mail as email_module

DEFAULT_USER = os.getenv("DEFAULT_USER", "ccc")
DEFAULT_PASS = os.getenv("DEFAULT_PASS", "cccpass")
BOX5_MODE = multi_mode.MODE
BOX5_ROOT = multi_mode.ROOT
BOX5_SIMPLE_KEY = multi_mode.SIMPLE_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONTAINER_DIR, exist_ok=True)

    if BOX5_MODE == "simple":
        multi_mode.init_simple_mode()
    elif BOX5_MODE == "multi":
        multi_mode.init_multi_mode()
    else:
        multi_mode.init_docker_mode()
        user_dir = os.path.join(UPLOAD_DIR, DEFAULT_USER)
        if not os.path.exists(user_dir):
            print(f"Creating default user: {DEFAULT_USER}")
            if create_user_container(DEFAULT_USER, DEFAULT_PASS):
                token_file = os.path.join(user_dir, ".token")
                with open(token_file, "w") as f:
                    f.write(DEFAULT_USER)
                print(f"Default user '{DEFAULT_USER}' created successfully!")
            else:
                print(f"Warning: Failed to create default user container")
        else:
            print(f"Default user '{DEFAULT_USER}' already exists")

    yield


app = FastAPI(title="Box5 Docker", version="0.1.0", lifespan=lifespan)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SCRIPT_DIR, "static")
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
UPLOAD_DIR = os.path.join(SCRIPT_DIR, "uploads")
CONTAINER_DIR = os.path.join(SCRIPT_DIR, "containers")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SERVER_PORT = 3111
SSH_PORT = 22
BASE_SSH_PORT = int(os.getenv("BOX5_SSH_BASE_PORT", "22000"))
BASE_HOST = os.getenv("BOX5_HOST", "localhost")
CONTAINER_IMAGE = os.getenv("BOX5_IMAGE", "box5-server:latest")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def get_container_name(username: str) -> str:
    """根據使用者名稱產生對應的 Docker 容器名稱"""
    return f"box5-{username}"


def create_user_in_container(container, username: str, password: str) -> bool:
    """在容器內建立系統使用者（SSH 用）"""
    try:
        result = container.exec_run(f"useradd -m -s /bin/zsh {username}")
        if result.exit_code != 0:
            output = result.output.decode() if result.output else ""
            print(f"useradd warning: {output}")

        result = container.exec_run(f"echo '{username}:{password}' | chpasswd")
        if result.exit_code != 0:
            output = result.output.decode() if result.output else ""
            print(f"chpasswd failed: {output}")
            return False

        result = container.exec_run(f"grep '^{username}:' /etc/shadow")
        output = result.output.decode() if result.output else ""
        if result.exit_code == 0:
            shadow_line = output.strip()
            if ':' in shadow_line:
                fields = shadow_line.split(':')
                pw_field = fields[1] if len(fields) > 1 else ""
                if pw_field == "!" or pw_field == "*" or not pw_field:
                    print(f"Password not set properly (pw_field: {pw_field}), retrying...")
                    result = container.exec_run(f"bash -c 'echo {username}:{password} | chpasswd'")
                    if result.exit_code != 0:
                        return False

        return True
    except Exception as e:
        print(f"Error creating user in container: {e}")
        return False


def get_ssh_port(username: str) -> int:
    """根據 username 計算 SSH 埠號"""
    user_dir = os.path.join(UPLOAD_DIR, username)
    ssh_port_file = os.path.join(user_dir, ".ssh_port")
    if os.path.exists(ssh_port_file):
        try:
            with open(ssh_port_file, "r") as f:
                port = f.read().strip()
                if port:
                    return int(port)
        except:
            pass
    return BASE_SSH_PORT + (sum(ord(c) for c in username) % 10000)


def get_user_port(username: str) -> int:
    """根據使用者名稱的雜湊值產生連接埠號（已棄用，改用實際 port mapping）"""
    return hash(username) % 10000 + 20000


class LoginRequest(BaseModel):
    username: str
    password: str


def create_user_container(username: str, password: str) -> bool:
    """為使用者建立 Docker 容器，設定環境變數與 Volume Mount，並等待 API 就緒後註冊使用者"""
    container_name = get_container_name(username)
    user_port = get_user_port(username)
    user_dir = os.path.join(UPLOAD_DIR, username)
    container_dir = os.path.join(CONTAINER_DIR, username)

    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(container_dir, exist_ok=True)
    
    sync_folder = os.path.join(user_dir, "sync")
    if not os.path.exists(sync_folder):
        sync_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sync")
        if os.path.exists(sync_src):
            import shutil
            shutil.copytree(sync_src, sync_folder)
        else:
            os.makedirs(sync_folder, exist_ok=True)
    
    local_sync_path = os.path.join(os.path.abspath(UPLOAD_DIR), username, "sync")

    try:
        existing = get_client().containers.get(container_name)
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass
    except Exception:
        pass

    try:
        nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
        env_vars = [
            f"USERNAME={username}",
            f"PASSWORD={password}",
            f"PORT={SERVER_PORT}",
            f"UPLOAD_DIR=/data/uploads/{username}",
            f"DB_PATH=/data/uploads/{username}/box5.db",
        ]
        if nvidia_key:
            env_vars.append(f"NVIDIA_API_KEY={nvidia_key}")

        container = get_client().containers.run(
            CONTAINER_IMAGE,
            name=container_name,
            detach=True,
            ports={
                f"{SERVER_PORT}/tcp": None,
                f"{SSH_PORT}/tcp": None,
            },
            environment=env_vars,
            volumes={
                os.path.abspath(UPLOAD_DIR): {"bind": "/data/uploads", "mode": "rw"},
                os.path.abspath(CONTAINER_DIR): {"bind": "/data/containers", "mode": "rw"},
                local_sync_path: {"bind": "/tmp/box5/sync", "mode": "rw"}
            },
            remove=False,
            network_mode="bridge"
        )
        
        import time
        for i in range(10):
            container.reload()
            port_mapping = container.ports.get(f"{SERVER_PORT}/tcp")
            if port_mapping:
                break
            time.sleep(1)
        
        if not port_mapping:
            print(f"Warning: No port mapping found for container after 10 attempts")
            return False
            
        actual_port = port_mapping[0]["HostPort"]
        print(f"Container assigned to port: {actual_port}")
        
        user_port = int(actual_port)
        
        for i in range(15):
            try:
                import requests as req
                test_url = f"http://localhost:{user_port}/api/health"
                req.get(test_url, timeout=2)
                print(f"Container API ready on port {user_port}")
                break
            except Exception as e:
                print(f"Waiting for container... attempt {i+1}")
                time.sleep(1)
        
        for attempt in range(5):
            try:
                import requests as req
                api_url = f"http://localhost:{user_port}/api/register"
                resp = req.post(api_url, json={"username": username, "password": password}, timeout=10)
                print(f"Register attempt {attempt+1}: status={resp.status_code}, response={resp.text[:100]}")
                if resp.status_code == 200:
                    print(f"User registered successfully!")
                    break
            except Exception as e:
                print(f"Registration attempt {attempt+1} failed: {e}")
                time.sleep(2)
        
        port_file = os.path.join(user_dir, ".port")
        with open(port_file, "w") as f:
            f.write(str(user_port))
        print(f"Saved port {user_port} to {port_file}")

        ssh_port_mapping = container.ports.get(f"{SSH_PORT}/tcp")
        if ssh_port_mapping:
            ssh_port = int(ssh_port_mapping[0]["HostPort"])
            ssh_port_file = os.path.join(user_dir, ".ssh_port")
            with open(ssh_port_file, "w") as f:
                f.write(str(ssh_port))
            print(f"Saved SSH port {ssh_port} to {ssh_port_file}")
        else:
            print("Warning: No SSH port mapping found")
            ssh_port = get_ssh_port(username)

        if not create_user_in_container(container, username, password):
            print("Warning: Failed to create SSH user in container")

        for i in range(10):
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", ssh_port))
                sock.close()
                if result == 0:
                    print(f"SSH ready on port {ssh_port}")
                    break
                time.sleep(1)
            except Exception as e:
                print(f"Waiting for SSH... attempt {i+1}")
                time.sleep(1)

        import shutil
        sync_src = os.path.join(CONTAINER_DIR, username, "sync")
        sync_dest = os.path.join(user_dir, "sync")
        if os.path.exists(sync_src) and not os.path.exists(sync_dest):
            shutil.copytree(sync_src, sync_dest)
            print(f"Copied sync folder to user directory")

        return True
    except Exception as e:
        import traceback
        print(f"Error creating container: {e}")
        traceback.print_exc()
        return False


def get_user_server_url(username: str) -> str:
    """取得使用者容器的完整伺服器 URL"""
    user_port = get_user_port(username)
    return f"http://{BASE_HOST}:{user_port}"


def get_user_port(username: str) -> int:
    user_dir = os.path.join(UPLOAD_DIR, username)
    port_file = os.path.join(user_dir, ".port")
    if os.path.exists(port_file):
        try:
            with open(port_file, "r") as f:
                port = f.read().strip()
                if port:
                    return int(port)
        except:
            pass
    try:
        container_name = get_container_name(username)
        container = get_client().containers.get(container_name)
        port_mapping = container.ports.get(f"{SERVER_PORT}/tcp")
        if port_mapping and port_mapping[0].get("HostPort"):
            return int(port_mapping[0]["HostPort"])
    except:
        pass
    return 20000 + (sum(ord(c) for c in username) % 10000)

def get_user_api(username: str) -> str:
    return f"{get_user_server_url(username)}/api"


def stop_user_container(username: str) -> bool:
    """停止使用者的 Docker 容器"""
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
    """強制移除使用者的 Docker 容器"""
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
    """查詢使用者容器的目前狀態（running/not_found/docker_unavailable/error）"""
    container_name = get_container_name(username)
    try:
        container = get_client().containers.get(container_name)
        return container.status
    except docker.errors.NotFound:
        return "not_found"
    except docker.errors.DockerException:
        return "docker_unavailable"
    except Exception:
        return "error"


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, folder: str = ""):
    token = request.cookies.get("token")
    username = request.cookies.get("username")
    if not token or not username:
        return RedirectResponse(url="/login")

    user_dir = os.path.join(UPLOAD_DIR, username)
    sync_folder = os.path.join(user_dir, "sync")
    if not os.path.exists(sync_folder):
        os.makedirs(sync_folder, exist_ok=True)
    
    if not folder:
        folder = "sync"

    files = []
    subfolders = []
    
    try:
        resp = requests.get(f"{get_user_api(username)}/files?folder={folder}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 401:
            return RedirectResponse(url="/login")
        if resp.status_code == 200:
            files = resp.json()
        subfolders = get_subfolders(username, token, folder)
    except:
        pass
    
    container_status = check_container_status(username)
    if container_status == "running" and token:
        try:
            api_folder = folder if folder else "sync"
            resp = requests.get(f"{get_user_api(username)}/files?folder={api_folder}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if resp.status_code == 200:
                db_files = resp.json()
                if db_files:
                    files = db_files
            subfolders = get_subfolders(username, token, api_folder)
        except Exception as e:
            print(f"API file listing error: {e}")
    
    if not files:
        user_dir = os.path.join(UPLOAD_DIR, username)
        sync_folder = os.path.join(user_dir, "sync")
        api_folder = folder if folder else "sync"
        if api_folder != "sync":
            sync_folder = os.path.join(user_dir, api_folder)
        
        if os.path.exists(sync_folder):
            try:
                for item in os.listdir(sync_folder):
                    item_path = os.path.join(sync_folder, item)
                    if os.path.isfile(item_path):
                        files.append({
                            "filename": item,
                            "filepath": item_path,
                            "size": os.path.getsize(item_path),
                            "is_public": 0
                        })
                    elif os.path.isdir(item_path):
                        subfolders.append(item)
            except Exception as e:
                print(f"File listing error: {e}")
    
    return templates.TemplateResponse(request=request, name="index.html", context={
        "files": files,
        "subfolders": subfolders,
        "current_folder": folder,
        "username": username
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

    if not os.path.exists(user_dir):
        return HTMLResponse(content="<h1>User not found</h1><a href='/login'>Try again</a>", status_code=401)

    container_status = check_container_status(username)
    if container_status == "docker_unavailable":
        return HTMLResponse(content="""<h1>Docker Unavailable</h1>
            <p>Docker is not running. Please start Docker Desktop and try again.</p>
            <a href='/login'>Try again</a>""", status_code=500)
    if container_status != "running":
        stored_password = os.getenv("DEFAULT_PASS") if username == DEFAULT_USER else None
        if not create_user_container(username, stored_password or password):
            return HTMLResponse(content="""<h1>Docker Error</h1>
            <p>Failed to create user container. Please ensure:</p>
            <ul>
                <li>Docker Desktop is running</li>
                <li>Box5 image is built: docker build -f Dockerfile.box5 -t box5-server:latest .</li>
            </ul>
            <a href='/login'>Try again</a>""", status_code=500)

    try:
        resp = requests.post(f"{get_user_api(username)}/login", json={"username": username, "password": password}, timeout=10)
        if resp.status_code != 200:
            return HTMLResponse(content="<h1>Login failed - wrong password or container not ready</h1><a href='/login'>Try again</a>", status_code=401)
        token = resp.json()["access_token"]
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="token", value=token)
        response.set_cookie(key="username", value=username)
        return response
    except requests.exceptions.ConnectionError:
        return HTMLResponse(content="""<h1>Container not running</h1>
            <p>Your container is not running. Please check Docker.</p>
            <a href='/login'>Try again</a>""", status_code=500)
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
        user_dir = os.path.join(UPLOAD_DIR, username)
        if not path.startswith("sync/"):
            local_path = os.path.join(user_dir, "sync", path)
        else:
            local_path = os.path.join(user_dir, path)
        
        if not os.path.exists(local_path) and not path.startswith("sync"):
            local_path = os.path.join(user_dir, path)
        if os.path.exists(local_path) and os.path.isfile(local_path):
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1].lower()
            
            if ext in [".jpg", ".jpeg"]:
                return FileResponse(local_path, media_type="image/jpeg")
            elif ext == ".png":
                return FileResponse(local_path, media_type="image/png")
            elif ext == ".gif":
                return FileResponse(local_path, media_type="image/gif")
            elif ext == ".webp":
                return FileResponse(local_path, media_type="image/webp")
            elif ext == ".svg":
                return FileResponse(local_path, media_type="image/svg+xml")
            elif ext in [".pdf"]:
                return FileResponse(local_path, media_type="application/pdf")
            
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            if ext == ".md":
                content = markdown.markdown(content)
                return HTMLResponse(content=f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{filename}</title><style>
body{{font-family:system-ui;padding:20px;max-width:800px;margin:0 auto}}
img{{max-width:100%}}pre{{background:#f5f5f5;padding:15px;border-radius:5px;overflow-x:auto}}
</style></head><body><h2>{path}</h2>{content}</body></html>""")
            elif ext == ".html":
                return HTMLResponse(content=content, media_type="text/html")
            
            code_exts = [".py", ".js", ".ts", ".c", ".h", ".cpp", ".sh", ".bash", ".zsh", ".go", ".rs", ".java", ".cs", ".rb", ".php", ".css", ".json", ".yaml", ".yml", ".xml", ".sql", ".swift", ".kt", ".scala", ".lua", ".pl"]
            if ext in code_exts or ext == ".txt":
                lang = ext[1:] if ext != ".txt" else "text"
                md_content = f"## {path}\n\n```{lang}\n{content}\n```"
                html_content = markdown.markdown(md_content, extensions=['fenced_code'])
                return HTMLResponse(content=f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{filename}</title><style>
body{{font-family:system-ui;padding:20px;max-width:800px;margin:0 auto}}
h2{{margin-bottom:15px;padding-bottom:10px;border-bottom:1px solid #ddd}}
pre{{background:#f5f5f5;padding:15px;border-radius:5px;overflow-x:auto}}
code{{font-family:monospace}}
</style></head><body>{html_content}</body></html>""", media_type="text/html")
            
            return HTMLResponse(content=f"<pre>{content}</pre>")
        
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


@app.get("/api/ssh/{username}")
async def get_ssh_info(username: str):
    if BOX5_MODE != "docker":
        return JSONResponse({"error": "SSH only available in docker mode"}, status_code=403)
    ssh_port = get_ssh_port(username)
    return {
        "host": BASE_HOST,
        "port": ssh_port,
        "username": username,
        "command": f"ssh {username}@{BASE_HOST} -p {ssh_port}"
    }


@app.post("/api/simple/login")
async def api_simple_login(request: Request):
    if BOX5_MODE == "simple":
        if BOX5_SIMPLE_KEY:
            incoming_key = request.headers.get("X-Simple-Key", "")
            if incoming_key != BOX5_SIMPLE_KEY:
                return JSONResponse({"error": "Invalid simple key"}, status_code=401)
        token = auth.create_access_token(1, "simple")
        return {"access_token": token}
    return JSONResponse({"error": "Simple login only available in simple mode"}, status_code=403)


@app.post("/api/auth/register")
async def api_register(request: Request):
    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    username = body.get("username", "").strip()
    password = body.get("password", "")
    email = body.get("email", "").strip()

    if not username or len(username) < 3:
        return JSONResponse({"error": "Username must be at least 3 characters"}, status_code=400)
    if not password or len(password) < 6:
        return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)

    try:
        user_id = auth.create_user(username, password, email)
    except Exception as e:
        print(f"Register error: {e}")
        return JSONResponse({"error": "Registration failed"}, status_code=500)
    if not user_id:
        return JSONResponse({"error": "Username already exists"}, status_code=400)

    if email and email_module:
        token = auth.create_verify_token()
        db = get_db()
        db.execute("UPDATE user_profiles SET verify_token = ? WHERE user_id = ?", (token, user_id))
        db.commit()
        db.close()
        email_module.send_verification_email(email, username, token)

    return {"message": "User registered", "user_id": user_id}


@app.post("/api/auth/login")
async def api_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = auth.get_user_by_username(username)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return HTMLResponse(content="<h1>Invalid credentials</h1><a href='/login'>Try again</a>", status_code=401)

    import socket
    client_ip = socket.gethostname()
    auth.record_login(user["id"], client_ip, "")

    token = auth.create_access_token(user["id"], user["username"])
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="token", value=token)
    response.set_cookie(key="username", value=user["username"])
    return response


@app.get("/api/auth/me")
async def api_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"error": "No token"}, status_code=401)
    payload = auth.decode_token(token)
    if not payload:
        return JSONResponse({"error": "Invalid token"}, status_code=401)
    user = auth.get_user_by_id(int(payload["sub"]))
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    profile = auth.get_user_profile(user["id"])
    return {
        "id": user["id"],
        "username": user["username"],
        "created_at": user["created_at"],
        "email": profile.get("email") if profile else None,
        "email_verified": profile.get("email_verified", 0) if profile else 0,
    }


@app.get("/api/auth/login-history")
async def api_login_history(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"error": "No token"}, status_code=401)
    payload = auth.decode_token(token)
    if not payload:
        return JSONResponse({"error": "Invalid token"}, status_code=401)
    history = auth.get_login_history(int(payload["sub"]))
    return history


@app.post("/api/keys")
async def api_create_key(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"error": "No token"}, status_code=401)
    payload = auth.decode_token(token)
    if not payload:
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = body.get("name", "My API Key")
    permissions = body.get("permissions", "read")
    if permissions not in ("read", "write", "admin"):
        permissions = "read"
    expires_at = body.get("expires_at", "")

    raw_key, key_id = auth.create_api_key(int(payload["sub"]), name, permissions, expires_at)
    return {"id": key_id, "key": raw_key, "name": name, "permissions": permissions}


@app.get("/api/keys")
async def api_list_keys(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"error": "No token"}, status_code=401)
    payload = auth.decode_token(token)
    if not payload:
        return JSONResponse({"error": "Invalid token"}, status_code=401)
    keys = auth.get_api_keys(int(payload["sub"]))
    return keys


@app.delete("/api/keys/{key_id}")
async def api_revoke_key(request: Request, key_id: int):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse({"error": "No token"}, status_code=401)
    payload = auth.decode_token(token)
    if not payload:
        return JSONResponse({"error": "Invalid token"}, status_code=401)
    auth.revoke_api_key(key_id, int(payload["sub"]))
    return {"message": "Key revoked"}


@app.get("/verify-email")
async def verify_email_page(request: Request, token: str = ""):
    if not token:
        return templates.TemplateResponse(request=request, name="verify-email.html", context={"success": False, "message": "No token provided"})
    db = get_db()
    row = db.execute("SELECT user_id FROM user_profiles WHERE verify_token = ?", (token,)).fetchone()
    if not row:
        db.close()
        return templates.TemplateResponse(request=request, name="verify-email.html", context={"success": False, "message": "Invalid token"})
    auth.verify_user_email(row["user_id"])
    db.close()
    return templates.TemplateResponse(request=request, name="verify-email.html", context={"success": True})


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot-password.html")


@app.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...), username: str = Form(...)):
    db = get_db()
    row = db.execute(
        "SELECT u.id FROM users u JOIN user_profiles up ON u.id = up.user_id WHERE u.username = ? AND up.email = ?",
        (username, email)
    ).fetchone()
    db.close()
    if not row:
        return templates.TemplateResponse(request=request, name="forgot-password.html", context={"error": "User not found"})
    token = auth.set_reset_token(row["id"])
    email_module.send_password_reset_email(email, username, token)
    return templates.TemplateResponse(request=request, name="forgot-password.html", context={"sent": True})


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    if not token:
        return templates.TemplateResponse(request=request, name="reset-password.html", context={"expired": True})
    user = auth.get_user_by_reset_token(token)
    if not user:
        return templates.TemplateResponse(request=request, name="reset-password.html", context={"expired": True})
    return templates.TemplateResponse(request=request, name="reset-password.html", context={"token": token})


@app.post("/reset-password")
async def reset_password_submit(request: Request, token: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    user = auth.get_user_by_reset_token(token)
    if not user:
        return templates.TemplateResponse(request=request, name="reset-password.html", context={"expired": True})
    if password != confirm:
        return templates.TemplateResponse(request=request, name="reset-password.html", context={"token": token, "error": "Passwords do not match"})
    if len(password) < 6:
        return templates.TemplateResponse(request=request, name="reset-password.html", context={"token": token, "error": "Password must be at least 6 characters"})

    auth.update_user_password(user["id"], password)
    auth.clear_reset_token(user["id"])

    try:
        import docker as docker_lib
        container_name = f"box5-{user['username']}"
        client = docker_lib.from_env()
        container = client.containers.get(container_name)
        container.exec_run(f"bash -c 'echo {user['username']}:{password} | chpasswd'")
    except Exception as e:
        print(f"Warning: Could not sync container password: {e}")

    return templates.TemplateResponse(request=request, name="reset-password.html", context={"success": True})


def require_admin(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="No token")
    payload = auth.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not admin_module.is_admin_user(int(payload["sub"])):
        raise HTTPException(status_code=403, detail="Admin required")
    return int(payload["sub"])


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/login")
    page = int(request.query_params.get("page", 1))
    search = request.query_params.get("search", "")
    sort_by = request.query_params.get("sort_by", "created_at")
    order = request.query_params.get("order", "desc")
    result = admin_module.get_all_users(page, 20, search, sort_by, order)
    return templates.TemplateResponse(request=request, name="admin/users.html", context={**result})


@app.get("/api/admin/dashboard")
async def api_admin_dashboard(request: Request):
    require_admin(request)
    return admin_module.get_dashboard_stats()


@app.get("/api/admin/users")
async def api_admin_users(request: Request):
    require_admin(request)
    page = int(request.query_params.get("page", 1))
    search = request.query_params.get("search", "")
    sort_by = request.query_params.get("sort_by", "created_at")
    order = request.query_params.get("order", "desc")
    return admin_module.get_all_users(page, 20, search, sort_by, order)


@app.get("/api/admin/users/{user_id}")
async def api_admin_user_detail(request: Request, user_id: int):
    require_admin(request)
    user = admin_module.get_user_detail(user_id)
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return user


@app.put("/api/admin/users/{user_id}")
async def api_admin_update_user(request: Request, user_id: int):
    require_admin(request)
    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    admin_module.update_user(user_id,
        quota_gb=body.get("quota_gb"),
        is_active=int(body.get("is_active", 1)),
        is_admin=int(body.get("is_admin", 0)),
    )
    return {"message": "User updated"}


@app.delete("/api/admin/users/{user_id}")
async def api_admin_delete_user(request: Request, user_id: int):
    require_admin(request)
    ok = admin_module.delete_user(user_id)
    if not ok:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return {"message": "User deleted"}


@app.post("/api/admin/users/{user_id}/reset-password")
async def api_admin_reset_password(request: Request, user_id: int):
    require_admin(request)
    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    new_password = body.get("password", "")
    if len(new_password) < 6:
        return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)
    ok = admin_module.reset_user_password(user_id, new_password)
    if not ok:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return {"message": "Password reset"}


@app.get("/api/admin/containers")
async def api_admin_containers(request: Request):
    require_admin(request)
    return admin_module.get_all_containers()


@app.post("/api/admin/containers/{username}/restart")
async def api_admin_restart_container(request: Request, username: str):
    require_admin(request)
    ok = admin_module.restart_container(username)
    if not ok:
        return JSONResponse({"error": "Container not found"}, status_code=404)
    return {"message": "Container restarted"}


@app.delete("/api/admin/containers/{username}")
async def api_admin_delete_container(request: Request, username: str):
    require_admin(request)
    admin_module.delete_container(username)
    return {"message": "Container deleted"}


@app.get("/api/admin/containers/{username}/logs")
async def api_admin_container_logs(request: Request, username: str, lines: int = 100):
    require_admin(request)
    logs = admin_module.get_container_logs(username, lines)
    return {"logs": logs}


@app.get("/admin/containers", response_class=HTMLResponse)
async def admin_containers_page(request: Request):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="admin/containers.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)