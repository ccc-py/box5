# box5

A personal Dropbox-like app with Client (desktop sync), Server (cloud storage), and Website (web UI).

## Quick Start

### 1. Start Server (port 3111)
```bash
cd Server && uvicorn main:app --reload --port 3111
```

### 2. Start Website (port 3112)
```bash
cd Website && uvicorn main:app --reload --port 3112
```

### 3. Start Client Sync
```bash
cd Client && python -m Client.main --username USER --password PASS --folder ./sync
```

## Web Interface
- Open browser: `http://localhost:3112`
- Register → Login → Upload/manage files
- `.md` files auto-render to HTML (customizable via `dbox5.css`)

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
- `Website/` — Web UI with Jinja2 templates + markdown rendering
- `tests/` — pytest unit tests
- `_doc/` — planning docs and version notes