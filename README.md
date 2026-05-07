# box5

A personal Dropbox-like app with Client (desktop sync), Server (cloud storage), and Website (web UI).

## Quick Start

### Start All Services
```bash
./run.sh
```
- Server: http://localhost:3111
- Website: http://localhost:3112

### Manual Start
```bash
# Server (port 3111)
cd Server && uvicorn main:app --port 3111

# Website (port 3112)
cd Website && uvicorn main:app --port 3112

# Client Sync
python -m Client.main --username ccc --password cccpass --folder ./sync
```

## Features

### File Sync
- Place files in `./sync/` folder to auto-upload
- Changes detected and synced automatically
- Use `./sync/public/` for public files (accessible without login)

### Folder Navigation (ls-style)
- Root shows subfolders: `subdir/`, `public/`
- Click folder to enter
- In subfolder shows `../` to go back
- Breadcrumb shows current path

### File Version History
- Same filename shows only latest version on homepage
- Click "History" to see all versions (v1, v2, v3...)

### File Viewer
- `.md` → Markdown rendered
- `.txt` → Plain text display
- `.jpg/.png/.gif` → Image display
- Other files → Download

### Public Files
- Files in `sync/public/` are uploaded as public
- Access via `/api/public/files` or Website `/public`

## Run Tests
```bash
./test.sh
```

## Tech Stack
- Python + FastAPI + sql5
- sql5 source: `/Users/Shared/ccc/project/sql5`

## Project Structure
- `Server/` — FastAPI server with sql5 database
- `Client/` — Desktop sync client using watchdog
- `Website/` — Web UI with Jinja2 templates
- `tests/` — pytest unit tests
- `_doc/` — planning docs and version notes