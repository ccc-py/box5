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
async def list_files(path: str = "/Users/Shared/ccc/project/box5/sync"):
    result = await handle_file_list(path)
    return result

@app.get("/api/editor/file")
async def read_file(path: str):
    result = await handle_file_read(path)
    return result

@app.post("/api/editor/file")
async def write_file(path: str, content: str):
    result = await handle_file_write(path, content)
    return result

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