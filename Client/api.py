import requests
from typing import Optional, List, Dict
from Client.config import SERVER_URL

class ApiClient:
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.token: Optional[str] = None

    def register(self, username: str, password: str) -> Dict:
        resp = requests.post(f"{self.base_url}/api/register", json={
            "username": username,
            "password": password
        })
        resp.raise_for_status()
        return resp.json()

    def login(self, username: str, password: str) -> str:
        resp = requests.post(f"{self.base_url}/api/login", json={
            "username": username,
            "password": password
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        return self.token

    def upload_file(self, filepath: str, folder: str = "", is_public: bool = False) -> Dict:
        if not self.token:
            raise ValueError("Not logged in")
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{self.base_url}/api/files/upload",
                files={"file": f},
                data={"folder": folder, "is_public": "true" if is_public else "false"},
                headers={"Authorization": f"Bearer {self.token}"}
            )
        resp.raise_for_status()
        return resp.json()

    def list_files(self) -> List[Dict]:
        if not self.token:
            raise ValueError("Not logged in")
        resp = requests.get(
            f"{self.base_url}/api/files",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp.raise_for_status()
        return resp.json()

    def download_file(self, file_id: int, dest_path: str) -> None:
        if not self.token:
            raise ValueError("Not logged in")
        resp = requests.get(
            f"{self.base_url}/api/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp.raise_for_status()
        data = resp.json()
        with open(data["filepath"], "rb") as src:
            with open(dest_path, "wb") as dst:
                dst.write(src.read())

    def delete_file(self, file_id: int) -> None:
        if not self.token:
            raise ValueError("Not logged in")
        resp = requests.delete(
            f"{self.base_url}/api/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp.raise_for_status()