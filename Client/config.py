import os

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:3111")
SYNC_FOLDER = os.getenv("SYNC_FOLDER", "./sync_folder")
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")