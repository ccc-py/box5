import os
import hashlib


def get_mode() -> str:
    return os.getenv("BOX5_MODE", "docker")


def get_root() -> str:
    return os.getenv("BOX5_ROOT", "")


def get_user_folder(username: str) -> str:
    root = get_root()
    return os.path.join(root, username) if root else ""


def check_path_allowed(path: str, username: str) -> bool:
    root = get_root()
    if not root:
        return True
    user_root = get_user_folder(username)
    try:
        abs_path = os.path.abspath(path)
        abs_user_root = os.path.abspath(user_root)
        return abs_path.startswith(abs_user_root)
    except Exception:
        return False


def resolve_user_path(path: str, username: str) -> str:
    root = get_root()
    if root:
        return os.path.join(root, username, path)
    return path


def is_public_path(path: str) -> bool:
    parts = path.strip("/").split("/")
    return len(parts) > 0 and parts[0] == "public"


def strip_public_prefix(path: str) -> str:
    if is_public_path(path):
        parts = path.strip("/").split("/", 1)
        return parts[1] if len(parts) > 1 else ""
    return path


def init_simple_mode():
    root = get_root()
    if root:
        os.makedirs(root, exist_ok=True)
        print(f"[Mode] Simple mode, root: {root}")
    else:
        print("[Mode] Simple mode, no root set")


def init_multi_mode():
    root = get_root()
    if root:
        os.makedirs(root, exist_ok=True)
        print(f"[Mode] Multi-user mode (no Docker), root: {root}")
    else:
        print("[Mode] Multi-user mode (no Docker), no root set")


def init_docker_mode():
    print("[Mode] Docker mode")


MODE = get_mode()
ROOT = get_root()
SIMPLE_KEY = os.getenv("BOX5_SIMPLE_KEY", "")