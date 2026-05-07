import os
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from typing import Optional
from Client.api import ApiClient
from Client.config import SYNC_FOLDER

class SyncHandler(FileSystemEventHandler):
    def __init__(self, api_client: ApiClient, sync_folder: str = SYNC_FOLDER):
        self.api = api_client
        self.sync_folder = sync_folder
        self.public_folder = os.path.join(sync_folder, "public")
        self.file_hashes: dict = {}

    def _get_file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _should_sync(self, filepath: str) -> bool:
        if not os.path.isfile(filepath):
            return False
        rel_path = os.path.relpath(filepath, self.sync_folder)
        if rel_path.startswith("."):
            return False
        return True

    def _is_public(self, filepath: str) -> bool:
        rel_path = os.path.relpath(filepath, self.sync_folder)
        return rel_path.startswith("public" + os.sep) or rel_path.startswith("public/")

    def _get_folder(self, filepath: str) -> str:
        rel_path = os.path.relpath(filepath, self.sync_folder)
        folder = os.path.dirname(rel_path)
        return folder if folder != "." else ""

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._should_sync(event.src_path):
            return
        print(f"File created: {event.src_path}")
        time.sleep(0.5)
        try:
            folder = self._get_folder(event.src_path)
            is_public = self._is_public(event.src_path)
            self.api.upload_file(event.src_path, folder=folder, is_public=is_public)
            self.file_hashes[event.src_path] = self._get_file_hash(event.src_path)
        except Exception as e:
            print(f"Upload failed: {e}")

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._should_sync(event.src_path):
            return
        current_hash = self._get_file_hash(event.src_path)
        old_hash = self.file_hashes.get(event.src_path)
        if current_hash != old_hash:
            print(f"File modified: {event.src_path}")
            time.sleep(0.5)
            try:
                folder = self._get_folder(event.src_path)
                is_public = self._is_public(event.src_path)
                self.api.upload_file(event.src_path, folder=folder, is_public=is_public)
                self.file_hashes[event.src_path] = current_hash
            except Exception as e:
                print(f"Upload failed: {e}")

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if event.src_path in self.file_hashes:
            del self.file_hashes[event.src_path]
        print(f"File deleted: {event.src_path}")

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        print(f"File moved: {event.src_path} -> {event.dest_path}")
        if event.src_path in self.file_hashes:
            self.file_hashes[event.dest_path] = self.file_hashes.pop(event.src_path)

class FolderWatcher:
    def __init__(self, api_client: ApiClient, sync_folder: str = SYNC_FOLDER):
        self.api = api_client
        self.sync_folder = sync_folder
        self.observer: Optional[Observer] = None
        self.handler = SyncHandler(api_client, sync_folder)

    def start(self):
        os.makedirs(self.sync_folder, exist_ok=True)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.sync_folder, recursive=True)
        self.observer.start()
        print(f"Watching {self.sync_folder} for changes...")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def initial_sync(self):
        print("Performing initial sync...")
        for root, dirs, files in os.walk(self.sync_folder):
            for filename in files:
                if filename.startswith("."):
                    continue
                filepath = os.path.join(root, filename)
                if self.handler._should_sync(filepath):
                    try:
                        folder = self.handler._get_folder(filepath)
                        is_public = self.handler._is_public(filepath)
                        self.api.upload_file(filepath, folder=folder, is_public=is_public)
                        self.handler.file_hashes[filepath] = self.handler._get_file_hash(filepath)
                        print(f"Uploaded: {filepath} (folder={folder}, public={is_public})")
                    except Exception as e:
                        print(f"Failed to upload {filepath}: {e}")