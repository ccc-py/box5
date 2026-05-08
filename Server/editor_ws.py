from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
import subprocess
import os
import asyncio
import xml.etree.ElementTree as ET

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.shell_processes: Dict[str, subprocess.Popen] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.shell_processes[client_id] = None

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.shell_processes:
            proc = self.shell_processes.pop(client_id, None)
            if proc:
                proc.terminate()
                proc.wait()

manager = ConnectionManager()

def parse_message(data: str) -> Dict[str, Any]:
    try:
        root = ET.fromstring(data)
        msg_type = root.get("type", "")
        content = {}
        for child in root:
            content[child.tag] = child.text or ""
        return {"type": msg_type, "content": content}
    except ET.ParseError:
        return {"type": "error", "content": {"message": "Invalid XML"}}

def create_response(msg_type: str, content: Dict[str, Any]) -> str:
    root = ET.Element("message", type=msg_type)
    for key, value in content.items():
        child = ET.SubElement(root, key)
        if isinstance(value, dict):
            child.text = json.dumps(value)
        elif isinstance(value, str):
            child.text = value
        else:
            child.text = str(value)
    return ET.tostring(root, encoding="unicode")

async def handle_terminal_input(client_id: str, command: str, cwd: str = None):
    if cwd:
        os.chdir(cwd)

    proc = manager.shell_processes.get(client_id)
    if proc and proc.poll() is None:
        proc.stdin.write(command.encode() + b"\n")
        proc.stdin.flush()
        return

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd or os.getcwd()
        )
        manager.shell_processes[client_id] = proc

        stdout, stderr = proc.communicate(timeout=30)
        result = {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "code": proc.returncode
        }
        return result
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"stdout": "", "stderr": "Command timeout", "code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "code": -1}

async def handle_file_read(path: str) -> Dict[str, Any]:
    try:
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            return {"error": "File not found", "content": "", "language": ""}

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ext = os.path.splitext(full_path)[1].lower()
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".html": "html", ".css": "css", ".json": "json",
            ".md": "markdown", ".txt": "text", ".sh": "shell",
            ".yaml": "yaml", ".yml": "yaml", ".xml": "xml"
        }
        language = lang_map.get(ext, "text")

        return {"content": content, "language": language, "path": full_path}
    except Exception as e:
        return {"error": str(e), "content": "", "language": ""}

async def handle_file_write(path: str, content: str) -> Dict[str, Any]:
    try:
        full_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "path": full_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def handle_file_list(path: str = ".") -> Dict[str, Any]:
    try:
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            return {"error": "Path not found", "files": []}

        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)
            items.append({
                "name": item,
                "path": item_path,
                "isDirectory": is_dir,
                "size": 0 if is_dir else os.path.getsize(item_path)
            })

        items.sort(key=lambda x: (not x["isDirectory"], x["name"]))
        return {"files": items, "path": full_path}
    except Exception as e:
        return {"error": str(e), "files": []}

async def websocket_endpoint(websocket: WebSocket):
    import logging
    logger = logging.getLogger(__name__)
    client_id = str(id(websocket))
    logger.info(f"WebSocket connecting: {client_id}")
    try:
        await websocket.accept()
        logger.info(f"WebSocket accepted: {client_id}")
        manager.active_connections[client_id] = websocket
        manager.shell_processes[client_id] = None
    except Exception as e:
        logger.error(f"WebSocket accept error: {e}")
        return

    try:
        while True:
            data = await websocket.receive_text()
            msg = parse_message(data)
            msg_type = msg.get("type", "")
            content = msg.get("content", {})

            if msg_type == "terminal_input":
                command = content.get("command", "")
                cwd = content.get("cwd", None)
                result = await handle_terminal_input(client_id, command, cwd)
                response = create_response("terminal_output", result)
                await websocket.send_text(response)

            elif msg_type == "file_read":
                path = content.get("path", "")
                result = await handle_file_read(path)
                response = create_response("file_content", result)
                await websocket.send_text(response)

            elif msg_type == "file_write":
                path = content.get("path", "")
                file_content = content.get("content", "")
                result = await handle_file_write(path, file_content)
                response = create_response("file_write_result", result)
                await websocket.send_text(response)

            elif msg_type == "file_list":
                path = content.get("path", ".")
                result = await handle_file_list(path)
                response = create_response("file_list_result", result)
                await websocket.send_text(response)

            elif msg_type == "shell_result":
                command = content.get("command", "")
                cwd = content.get("cwd", None)
                result = await handle_terminal_input(client_id, command, cwd)
                response = create_response("shell_output", result)
                await websocket.send_text(response)

            else:
                response = create_response("error", {"message": f"Unknown message type: {msg_type}"})
                await websocket.send_text(response)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        response = create_response("error", {"message": str(e)})
        try:
            await websocket.send_text(response)
        except:
            pass
        manager.disconnect(client_id)