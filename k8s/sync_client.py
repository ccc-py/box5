import os
import time
import hashlib
import threading
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from client import ApiClient


class SyncHandler(FileSystemEventHandler):
    def __init__(self, api: ApiClient, sync_folder: str, folder: str = ""):
        self.api = api
        self.sync_folder = os.path.abspath(sync_folder)
        self.folder = folder
        self.public_folder = os.path.join(sync_folder, "public")
        self.file_hashes: dict = {}
        self._ignore_next = set()

    def _should_sync(self, filepath: str) -> bool:
        if not os.path.isfile(filepath):
            return False
        rel_path = os.path.relpath(filepath, self.sync_folder)
        if rel_path.startswith("."):
            return False
        if "node_modules" in rel_path or "__pycache__" in rel_path:
            return False
        return True

    def _is_public(self, filepath: str) -> bool:
        rel_path = os.path.relpath(filepath, self.sync_folder)
        return rel_path.startswith("public" + os.sep) or rel_path.startswith("public/")

    def _get_subfolder(self, filepath: str) -> str:
        rel_path = os.path.relpath(filepath, self.sync_folder)
        parent = os.path.dirname(rel_path)
        if parent == "." or parent == "":
            return self.folder
        if rel_path.startswith("public" + os.sep) or rel_path.startswith("public/"):
            rest = rel_path[len("public/" if rel_path.startswith("public/") else "public" + os.sep):]
            parts = rest.split(os.sep)
            if len(parts) > 1:
                return f"{self.folder}/{'/'.join(parts[:-1])}" if self.folder else '/'.join(parts[:-1])
            return self.folder
        return f"{self.folder}/{parent}" if self.folder else parent

    def _file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _ignore(self, filepath: str):
        self._ignore_next.add(filepath)
        time.sleep(0.2)
        if filepath in self._ignore_next:
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
            folder = self._get_subfolder(event.src_path)
            is_public = self._is_public(event.src_path)
            self.api.upload_file(event.src_path, folder=folder, is_public=is_public)
            self.file_hashes[event.src_path] = self._file_hash(event.src_path)
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
        old = self.file_hashes.get(event.src_path)
        if current != old:
            print(f"[Sync] Modified: {event.src_path}")
            try:
                folder = self._get_subfolder(event.src_path)
                is_public = self._is_public(event.src_path)
                self.api.upload_file(event.src_path, folder=folder, is_public=is_public)
                self.file_hashes[event.src_path] = current
            except Exception as e:
                print(f"[Sync] Upload failed: {e}")

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self.file_hashes:
            del self.file_hashes[event.src_path]
        print(f"[Sync] Deleted: {event.src_path}")

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self.file_hashes:
            self.file_hashes[event.dest_path] = self.file_hashes.pop(event.src_path)
        print(f"[Sync] Moved: {event.src_path} -> {event.dest_path}")


class FolderWatcher:
    def __init__(self, api: ApiClient, sync_folder: str, folder: str = ""):
        self.api = api
        self.sync_folder = os.path.abspath(sync_folder)
        self.folder = folder
        self.observer: Optional[Observer] = None
        self.handler = SyncHandler(api, sync_folder, folder)

    def start(self):
        os.makedirs(self.sync_folder, exist_ok=True)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.sync_folder, recursive=True)
        self.observer.start()
        print(f"[Sync] Watching {self.sync_folder} for changes...")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("[Sync] Watcher stopped")

    def initial_sync(self):
        print("[Sync] Performing initial sync (pull from server)...")
        try:
            remote_files = self.api.list_files(folder=self.folder)
            for f in remote_files:
                local_path = os.path.join(self.sync_folder, f.get("folder", ""), f["filename"])
                if os.path.exists(local_path):
                    local_hash = self.api.get_file_hash(local_path)
                else:
                    local_hash = ""
                if not os.path.exists(local_path) or f.get("hash") != local_hash:
                    print(f"[Sync] Downloading: {f['filename']}")
                    self.api.download_file(f["id"], local_path)
        except Exception as e:
            print(f"[Sync] Initial sync failed: {e}")

    def full_sync(self):
        print("[Sync] Performing full sync (push local files)...")
        os.makedirs(self.sync_folder, exist_ok=True)
        for root, dirs, files in os.walk(self.sync_folder):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
            for filename in files:
                if filename.startswith("."):
                    continue
                filepath = os.path.join(root, filename)
                try:
                    folder = self.handler._get_subfolder(filepath)
                    is_public = self.handler._is_public(filepath)
                    self.api.upload_file(filepath, folder=folder, is_public=is_public)
                    self.handler.file_hashes[filepath] = self.handler._file_hash(filepath)
                    print(f"[Sync] Uploaded: {filepath}")
                except Exception as e:
                    print(f"[Sync] Upload failed: {e}")


def run_sync(server_url: str, username: str, password: str, sync_folder: str, folder: str = ""):
    print(f"[Sync] Starting local-mode sync client")
    print(f"[Sync] Server: {server_url}")
    print(f"[Sync] Folder: {sync_folder} -> remote: /{folder}")

    api = ApiClient(server_url)
    try:
        api.login(username, password)
        print("[Sync] Logged in successfully")
    except Exception as e:
        print(f"[Sync] Login failed: {e}")
        return

    watcher = FolderWatcher(api, sync_folder, folder)

    print("[Sync] Choose sync mode:")
    print("  1) Watch mode (watch for changes, bidirectional sync)")
    print("  2) Pull mode (download from server only)")
    print("  3) Push mode (upload local files only)")
    print("  4) Full sync (push then watch)")

    mode = input("Enter choice [1]: ").strip() or "1"

    if mode == "1":
        watcher.initial_sync()
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
    elif mode == "2":
        watcher.initial_sync()
    elif mode == "3":
        watcher.full_sync()
    elif mode == "4":
        watcher.full_sync()
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
    else:
        watcher.initial_sync()
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="box5 local sync client")
    parser.add_argument("--server", default=os.getenv("BOX5_SERVER", "http://localhost:8000"), help="Server URL")
    parser.add_argument("--user", default=os.getenv("BOX5_USER", ""), help="Username")
    parser.add_argument("--password", default=os.getenv("BOX5_PASS", ""), help="Password")
    parser.add_argument("--folder", default=os.getenv("BOX5_FOLDER", "./sync"), help="Sync folder")
    parser.add_argument("--remote", default="", help="Remote folder path")
    args = parser.parse_args()

    if not args.user or not args.password:
        print("Error: --user and --password required")
        import sys
        sys.exit(1)

    run_sync(args.server, args.user, args.password, args.folder, args.remote)
