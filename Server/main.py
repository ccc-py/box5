from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Server.database import init_db
from Server.routes import router
from Server.editor_ws import websocket_endpoint, handle_file_list, handle_file_read, handle_file_write

app = FastAPI(title="box5 Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(router, prefix="/api")

@app.get("/api/editor/files")
async def list_files(path: str = "./sync"):
    if not os.path.isabs(path):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(project_root, path)
    result = await handle_file_list(path)
    return result

@app.get("/api/editor/file")
async def read_file(path: str):
    result = await handle_file_read(path)
    return result

@app.post("/api/editor/file")
async def write_file(request: dict):
    path = request.get('path', '')
    content = request.get('content', '')
    result = await handle_file_write(path, content)
    return result

@app.delete("/api/editor/file")
async def delete_file(path: str):
    import os
    try:
        full_path = os.path.abspath(path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            return {"success": True, "message": "File deleted"}
        elif os.path.isdir(full_path):
            os.rmdir(full_path)
            return {"success": True, "message": "Directory deleted"}
        else:
            return {"success": False, "error": "File not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.websocket("/ws/editor")
async def ws_editor(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket_endpoint(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/health")
async def health():
    return {"status": "ok"}