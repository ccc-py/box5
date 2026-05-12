import os
import sys
import time
import hashlib
import argparse
import threading
import subprocess
from typing import Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

import requests


class SimpleApiClient:
    def __init__(self, base_url: str, simple_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.simple_key = simple_key
        self.token: Optional[str] = None

    def _headers(self):
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.simple_key:
            h["X-Simple-Key"] = self.simple_key
        return h

    def login(self, username: str, password: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/auth/login",
            data={"username": username, "password": password},
            timeout=10,
            headers=self._headers()
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            return self.token
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")

    def simple_login(self) -> str:
        resp = requests.post(
            f"{self.base_url}/api/simple/login",
            headers={"X-Simple-Key": self.simple_key} if self.simple_key else {},
            timeout=10
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            return self.token
        raise Exception(f"Simple login failed: {resp.status_code} {resp.text}")

    def list_files(self, folder: str = "") -> list:
        resp = requests.get(
            f"{self.base_url}/api/files",
            params={"folder": folder},
            headers=self._headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, filepath: str, folder: str = "", is_public: bool = False) -> dict:
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{self.base_url}/api/files/upload",
                files={"file": f},
                data={"folder": folder, "is_public": "true" if is_public else "false"},
                headers=self._headers(), timeout=30
            )
        resp.raise_for_status()
        return resp.json()

    def delete_file(self, file_id: int) -> bool:
        resp = requests.delete(
            f"{self.base_url}/api/files/{file_id}",
            headers=self._headers(), timeout=10
        )
        return resp.status_code == 200

    def get_file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()


class SimpleSyncHandler(FileSystemEventHandler):
    def __init__(self, api: SimpleApiClient, sync_folder: str, remote_folder: str = ""):
        self.api = api
        self.sync_folder = os.path.abspath(sync_folder)
        self.remote_folder = remote_folder
        self.local_hashes: dict = {}
        self._ignore_next: set = set()
        self._remote_files: dict = {}

    def _should_sync(self, filepath: str) -> bool:
        if not os.path.isfile(filepath):
            return False
        rel_path = os.path.relpath(filepath, self.sync_folder)
        if rel_path.startswith("."):
            return False
        if "node_modules" in rel_path or "__pycache__" in rel_path:
            return False
        return True

    def _file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _ignore(self, filepath: str):
        self._ignore_next.add(filepath)
        time.sleep(0.3)
        self._ignore_next.discard(filepath)

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self._ignore_next:
            return
        if not self._should_sync(event.src_path):
            return
        print(f"[Sync] Created: {event.src_path}")
        try:
            self._upload(event.src_path)
            self.local_hashes[event.src_path] = self._file_hash(event.src_path)
        except Exception as e:
            print(f"[Sync] Upload failed: {e}")

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self._ignore_next:
            return
        if not self._should_sync(event.src_path):
            return
        current = self._file_hash(event.src_path)
        old = self.local_hashes.get(event.src_path)
        if current != old:
            print(f"[Sync] Modified: {event.src_path}")
            try:
                self._upload(event.src_path)
                self.local_hashes[event.src_path] = current
            except Exception as e:
                print(f"[Sync] Upload failed: {e}")

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        filepath = event.src_path
        if filepath in self.local_hashes:
            del self.local_hashes[filepath]
        print(f"[Sync] Deleted: {event.src_path}")
        rel = os.path.relpath(filepath, self.sync_folder)
        for fid, rpath in list(self._remote_files.items()):
            if rpath == rel:
                try:
                    self.api.delete_file(fid)
                    del self._remote_files[fid]
                    print(f"[Sync] Remote file deleted: {rel}")
                except Exception as e:
                    print(f"[Sync] Remote delete failed: {e}")
                break

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self.local_hashes:
            self.local_hashes[event.dest_path] = self.local_hashes.pop(event.src_path)
        print(f"[Sync] Moved: {event.src_path} -> {event.dest_path}")
        rel_old = os.path.relpath(event.src_path, self.sync_folder)
        rel_new = os.path.relpath(event.dest_path, self.sync_folder)
        for fid, rpath in self._remote_files.items():
            if rpath == rel_old:
                self._remote_files[fid] = rel_new
                break

    def _upload(self, filepath: str):
        rel = os.path.relpath(filepath, self.sync_folder)
        folder = os.path.dirname(rel)
        if folder == ".":
            folder = self.remote_folder
        else:
            folder = f"{self.remote_folder}/{folder}" if self.remote_folder else folder
        self.api.upload_file(filepath, folder=folder)
        for f in self.api.list_files(folder=folder):
            if f["filename"] == os.path.basename(filepath):
                self._remote_files[f["id"]] = rel
                break

    def pull_remote(self, remote_files: list):
        for f in remote_files:
            local_path = os.path.join(self.sync_folder, f.get("folder", ""), f["filename"])
            local_path = os.path.normpath(local_path)
            rel = os.path.relpath(local_path, self.sync_folder)
            self._remote_files[f["id"]] = rel
            local_hash = self._file_hash(local_path)
            remote_hash = f.get("hash", "")
            if local_hash != remote_hash:
                print(f"[Sync] Downloading: {rel}")
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                resp = requests.get(
                    f"{self.api.base_url}/api/files/{f['id']}/download",
                    headers=self.api._headers(), timeout=30, stream=True
                )
                if resp.status_code == 200:
                    with open(local_path, "wb") as out:
                        for chunk in resp.iter_content(65536):
                            out.write(chunk)
                    self.local_hashes[local_path] = self._file_hash(local_path)

    def sync_to_server(self):
        for root, dirs, files in os.walk(self.sync_folder):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
            for filename in files:
                if filename.startswith("."):
                    continue
                filepath = os.path.join(root, filename)
                if not self._should_sync(filepath):
                    continue
                rel = os.path.relpath(filepath, self.sync_folder)
                folder = os.path.dirname(rel)
                if folder == ".":
                    folder = self.remote_folder
                else:
                    folder = f"{self.remote_folder}/{folder}" if self.remote_folder else folder
                try:
                    self._upload(filepath)
                    self.local_hashes[filepath] = self._file_hash(filepath)
                    print(f"[Sync] Uploaded: {rel}")
                except Exception as e:
                    print(f"[Sync] Upload failed: {e}")


def run_simple_sync(server_url: str, sync_folder: str, remote_folder: str,
                    username: str = "", password: str = "",
                    simple_key: str = "", watch: bool = True):
    print(f"[Sync] Starting simple sync client")
    print(f"[Sync] Server: {server_url}")
    print(f"[Sync] Local: {sync_folder} -> Remote: /{remote_folder}")

    api = SimpleApiClient(server_url, simple_key)

    if username and password:
        api.login(username, password)
        print("[Sync] Logged in with user account")
    else:
        api.simple_login()
        print("[Sync] Logged in with simple mode")

    remote_files = api.list_files(folder=remote_folder)
    print(f"[Sync] Remote has {len(remote_files)} files")

    if not HAS_WATCHDOG:
        print("[Sync] watchdog not installed, doing one-time sync only")
        handler = SimpleSyncHandler(api, sync_folder, remote_folder)
        handler.pull_remote(remote_files)
        handler.sync_to_server()
        return

    handler = SimpleSyncHandler(api, sync_folder, remote_folder)
    handler.pull_remote(remote_files)

    observer = Observer()
    observer.schedule(handler, sync_folder, recursive=True)
    observer.start()
    print(f"[Sync] Watching {sync_folder} for changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        print("[Sync] Stopped")


def main():
    parser = argparse.ArgumentParser(description="box5 simple sync client")
    parser.add_argument("--server", default=os.getenv("BOX5_SERVER", "http://localhost:8000"),
                        help="Server URL")
    parser.add_argument("--local-folder", default=os.getenv("BOX5_LOCAL_FOLDER", "./sync"),
                        help="Local sync folder")
    parser.add_argument("--remote-folder", default=os.getenv("BOX5_REMOTE_FOLDER", ""),
                        help="Remote folder path (empty = root)")
    parser.add_argument("--username", default=os.getenv("BOX5_USER", ""),
                        help="Username (optional, uses simple login if not set)")
    parser.add_argument("--password", default=os.getenv("BOX5_PASS", ""),
                        help="Password")
    parser.add_argument("--simple-key", default=os.getenv("BOX5_SIMPLE_KEY", ""),
                        help="Simple mode shared key")
    parser.add_argument("--no-watch", action="store_true",
                        help="One-time sync only (no watching)")

    args = parser.parse_args()

    if not os.path.exists(args.local_folder):
        os.makedirs(args.local_folder, exist_ok=True)
        print(f"[Sync] Created local folder: {args.local_folder}")

    try:
        run_simple_sync(
            server_url=args.server,
            sync_folder=args.local_folder,
            remote_folder=args.remote_folder,
            username=args.username,
            password=args.password,
            simple_key=args.simple_key,
            watch=not args.no_watch
        )
    except KeyboardInterrupt:
        print("\n[Sync] Interrupted, exiting")
        sys.exit(0)
    except Exception as e:
        print(f"[Sync] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()