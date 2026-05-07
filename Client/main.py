import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Client.config import SERVER_URL, SYNC_FOLDER, USERNAME, PASSWORD
from Client.api import ApiClient
from Client.sync import FolderWatcher

def main():
    parser = argparse.ArgumentParser(description="box5 Client")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    parser.add_argument("--folder", default=SYNC_FOLDER, help="Sync folder path")
    parser.add_argument("--username", default=USERNAME, help="Username")
    parser.add_argument("--password", default=PASSWORD, help="Password")
    args = parser.parse_args()

    if not args.username or not args.password:
        print("Error: username and password required")
        sys.exit(1)

    api = ApiClient(args.server)
    try:
        try:
            api.register(args.username, args.password)
            print(f"Registered new user: {args.username}")
        except Exception:
            pass
        api.login(args.username, args.password)
        print("Logged in successfully")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)

    watcher = FolderWatcher(api, args.folder)
    watcher.initial_sync()
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()
        print("Done")

if __name__ == "__main__":
    main()