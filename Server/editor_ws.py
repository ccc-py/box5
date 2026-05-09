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
        self.shell_processes: Dict[str, Any] = {}
        self.shell_readers: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id] = websocket
        self.shell_processes[client_id] = None
        self.shell_readers[client_id] = None

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        keys_to_remove = [k for k in self.shell_processes.keys() if k.startswith(f"{client_id}_") or k == client_id]
        for k in keys_to_remove:
            shell_info = self.shell_processes.pop(k, None)
            if shell_info:
                try:
                    if shell_info.get('master'):
                        os.close(shell_info['master'])
                    if shell_info.get('proc'):
                        shell_info['proc'].terminate()
                        shell_info['proc'].wait()
                except:
                    pass

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
    if msg_type == "terminal_output":
        output = ET.SubElement(root, "output")
        output.text = json.dumps(content)
    else:
        for key, value in content.items():
            child = ET.SubElement(root, key)
            if isinstance(value, dict):
                child.text = json.dumps(value)
            elif isinstance(value, str):
                child.text = value
            else:
                child.text = str(value)
    return ET.tostring(root, encoding="unicode")

def start_shell(session_key: str, cwd: str):
    try:
        import pty
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            ['/bin/zsh'],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=cwd,
            start_new_session=True,
            env=os.environ.copy()
        )
        os.close(slave)
        manager.shell_processes[session_key] = {
            'proc': proc,
            'master': master,
            'cwd': cwd
        }
        return True
    except Exception as e:
        print(f"Failed to start shell: {e}")
        return False


async def read_pty_output_continuous(client_id: str, terminal_id: str):
    import logging
    logger = logging.getLogger(__name__)
    session_key = f"{client_id}_{terminal_id}"

    while True:
        shell_info = manager.shell_processes.get(session_key)
        if not shell_info or not shell_info.get('master'):
            break

        try:
            master = shell_info['master']
            import select

            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    data = os.read(master, 4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        ws = manager.active_connections.get(client_id)
                        if ws:
                            result = {"stdout": text, "stderr": "", "code": 0, "terminal_id": terminal_id}
                            response = create_response("terminal_output", result)
                            try:
                                await ws.send_text(response)
                            except:
                                pass
                except OSError:
                    break
        except Exception as e:
            logger.error(f"Error reading PTY: {e}")
            break
        await asyncio.sleep(0.02)


async def read_pty_output(client_id: str, duration: float = 0.5):
    import logging
    logger = logging.getLogger(__name__)
    buffer = ""

    try:
        import time
        start_time = time.time()

        while time.time() - start_time < duration:
            shell_info = manager.shell_processes.get(client_id)
            if not shell_info or not shell_info.get('master'):
                break

            try:
                master = shell_info['master']
                import select

                ready, _, _ = select.select([master], [], [], 0.05)
                if ready:
                    try:
                        data = os.read(master, 4096)
                        if data:
                            buffer += data.decode('utf-8', errors='replace')
                    except OSError:
                        break
            except Exception as e:
                logger.error(f"Error reading PTY: {e}")
                break
            await asyncio.sleep(0.02)

        return buffer
    except Exception as e:
        return ""


async def send_pty_output(client_id: str, duration: float = 0.5):
    import logging
    logger = logging.getLogger(__name__)
    buffer = await read_pty_output(client_id, duration)

    if buffer:
        ws = manager.active_connections.get(client_id)
        if ws:
            result = {"stdout": buffer, "stderr": "", "code": 0}
            response = create_response("terminal_output", result)
            try:
                await ws.send_text(response)
            except:
                pass


async def handle_terminal_input(client_id: str, terminal_id: str, command: str, cwd: str = None, raw_data: str = None):
    import logging
    logger = logging.getLogger(__name__)
    session_key = f"{client_id}_{terminal_id}"

    # Resolve relative path to absolute
    if cwd and not os.path.isabs(cwd):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cwd = os.path.join(project_root, cwd)

    if not cwd:
        cwd = os.getcwd()

    # Get or create shell for this client
    shell_info = manager.shell_processes.get(session_key)

    # Check if shell needs to be started
    if not shell_info or not shell_info.get('proc'):
        if start_shell(session_key, cwd):
            asyncio.create_task(read_pty_output_continuous(client_id, terminal_id))
            shell_info = manager.shell_processes.get(session_key)
        else:
            return {"stdout": "", "stderr": "Failed to start shell", "code": -1, "terminal_id": terminal_id}

    master = shell_info['master']

    # Raw data bypassing lines and command buffering
    if raw_data is not None:
        try:
            os.write(master, raw_data.encode('utf-8'))
        except Exception as e:
            return {"stdout": "", "stderr": f"Shell error: {e}", "code": -1, "terminal_id": terminal_id}
        return None

    # Handle exit command - terminate shell
    if command.strip() == 'exit':
        try:
            os.close(shell_info['master'])
            shell_info['proc'].terminate()
            shell_info['proc'].wait()
        except:
            pass
        manager.shell_processes.pop(session_key, None)
        return {"stdout": "\r\nShell closed\r\n", "stderr": "", "code": 0, "terminal_id": terminal_id}

    # If it's just an empty command (used to initialize the shell)
    if not command.strip():
        # Shell is already started and continuous reader is running.
        return None

    # Legacy command processing fallback
    try:
        # Change directory if needed
        if shell_info.get('cwd') != cwd:
            os.write(master, f'cd "{cwd}"\n'.encode('utf-8'))
            shell_info['cwd'] = cwd
            await asyncio.sleep(0.1)

        cmd_to_send = command.strip() + '\n'
        os.write(master, cmd_to_send.encode('utf-8'))
    except Exception as e:
        return {"stdout": "", "stderr": f"Shell error: {e}", "code": -1, "terminal_id": terminal_id}
        
    return None


async def read_shell_output(client_id: str, proc: subprocess.Popen):
    import logging
    logger = logging.getLogger(__name__)
    try:
        while proc.poll() is None:
            try:
                # Read from stdout and stderr without blocking
                import select
                reads = []
                if proc.stdout:
                    reads.append(proc.stdout)
                if proc.stderr:
                    reads.append(proc.stderr)

                if reads:
                    ready, _, _ = select.select(reads, [], [], 0.1)
                    for r in ready:
                        try:
                            data = r.read1(1024)
                            if data:
                                ws = manager.active_connections.get(client_id)
                                if ws:
                                    result = {"stdout": data.decode("utf-8", errors="replace"), "stderr": "", "code": 0}
                                    response = create_response("terminal_output", result)
                                    await ws.send_text(response)
                        except:
                            pass
            except:
                pass
            await asyncio.sleep(0.05)
    except Exception as e:
        logger.error(f"Error reading shell output: {e}")

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
        manager.active_connections[client_id] = websocket
        manager.shell_processes[client_id] = None
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        return

    try:
        while True:
            data = await websocket.receive_text()
            msg = parse_message(data)
            msg_type = msg.get("type", "")
            content = msg.get("content", {})

            if msg_type == "terminal_input":
                raw_data_str = content.get("raw_data", None)
                command = content.get("command", "")
                cwd = content.get("cwd", None)
                terminal_id = content.get("terminal_id", "default")
                
                if raw_data_str:
                    raw_data = json.loads(raw_data_str)
                    result = await handle_terminal_input(client_id, terminal_id, command="", cwd=cwd, raw_data=raw_data)
                else:
                    result = await handle_terminal_input(client_id, terminal_id, command, cwd)
                    
                if result is not None:
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