# box5

A personal Dropbox-like app with Client (desktop sync), Server (cloud storage), and Website (web UI).

## Quick Start

### Start All Services (box5)
```bash
./run.sh
```
- Server: http://localhost:3111
- Website: http://localhost:3112

### Start K8s Version (multi-tenant with Docker)
```bash
cd k8s
./k8s_run.sh
```
- Web UI: http://localhost:8000

### Manual Start (box5)
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

### File Viewer (v1.0 Static Rendering)
- Files view natively via absolute path routes like `/view/public/ccc.md` 
- `.md` → Markdown rendered with true relative-link support layout (e.g., `./img/ccc.jpg`)
- `.txt` → Plain text display
- `.html/.css/.js` → Direct static site web response execution
- `.jpg/.png/.gif` → Native image display streaming
- Other files → Download

### Public Files
- Files in `sync/public/` are uploaded as public
- Access via `/api/public/files` or Website `/public`

### Web Editor
- Web-based code editor similar to VSCode (access at `/editor`)
- Monaco Editor for multi-tab code editing
- Integrated Terminal with real-time multiplexed PTY

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