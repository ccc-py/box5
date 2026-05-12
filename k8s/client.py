import os
import time
import hashlib
import requests
from typing import Optional, List, Dict


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None

    def login(self, username: str, password: str) -> str:
        resp = requests.post(f"{self.base_url}/api/auth/login",
            data={"username": username, "password": password}, timeout=10)
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            return self.token
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")

    def list_files(self, folder: str = "") -> List[Dict]:
        if not self.token:
            raise Exception("Not logged in")
        resp = requests.get(f"{self.base_url}/api/files",
            params={"folder": folder},
            headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, filepath: str, folder: str = "", is_public: bool = False) -> Dict:
        if not self.token:
            raise Exception("Not logged in")
        with open(filepath, "rb") as f:
            resp = requests.post(f"{self.base_url}/api/files/upload",
                files={"file": f},
                data={"folder": folder, "is_public": "true" if is_public else "false"},
                headers={"Authorization": f"Bearer {self.token}"}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def download_file(self, file_id: int, dest_path: str) -> bool:
        if not self.token:
            raise Exception("Not logged in")
        resp = requests.get(f"{self.base_url}/api/files/{file_id}/download",
            headers={"Authorization": f"Bearer {self.token}"}, timeout=30, stream=True)
        if resp.status_code != 200:
            return False
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
        return True

    def delete_file(self, file_id: int) -> bool:
        if not self.token:
            raise Exception("Not logged in")
        resp = requests.delete(f"{self.base_url}/api/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        return resp.status_code == 200

    def get_file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
