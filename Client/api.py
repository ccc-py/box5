import requests
from typing import Optional, List, Dict
from Client.config import SERVER_URL

class ApiClient:
    """封裝對伺服器 RESTful API 的 HTTP 請求，自動管理存取令牌"""
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.token: Optional[str] = None

    def register(self, username: str, password: str) -> Dict:
        """向伺服器註冊新使用者"""
        resp = requests.post(f"{self.base_url}/api/register", json={
            "username": username,
            "password": password
        })
        resp.raise_for_status()
        return resp.json()

    def login(self, username: str, password: str) -> str:
        """登入並取得存取令牌，後續請求都會帶入 Authorization 標頭"""
        resp = requests.post(f"{self.base_url}/api/login", json={
            "username": username,
            "password": password
        })
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        return self.token

    def upload_file(self, filepath: str, folder: str = "", is_public: bool = False) -> Dict:
        """以 multipart/form-data 格式上傳檔案"""
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
        """取得伺服器上的檔案列表"""
        if not self.token:
            raise ValueError("Not logged in")
        resp = requests.get(
            f"{self.base_url}/api/files",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp.raise_for_status()
        return resp.json()

    def download_file(self, file_id: int, dest_path: str) -> None:
        """透過檔案編號從伺服器下載檔案到本機指定路徑"""
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
        """通知伺服器刪除指定編號的檔案"""
        if not self.token:
            raise ValueError("Not logged in")
        resp = requests.delete(
            f"{self.base_url}/api/files/{file_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp.raise_for_status()