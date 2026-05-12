# box5 — Dropbox-like app (Client + Server + Website + k8s variant)

## Quick Start
```bash
./install.sh          # Install dependencies (run once)
./test.sh             # Run all tests (unit + API + E2E)
./run.sh              # Run server + website + client
```

## Core Commands
| Service | Command | Port |
|---------|---------|------|
| Server | `cd Server && uv run uvicorn main:app --reload --port 3111` | 3111 |
| Website | `cd Website && uv run uvicorn main:app --reload --port 3112` | 3112 |
| Client | `uv run python -m Client.main --username USER --password PASS --folder ./sync` | — |

**Default credentials:** `ccc` / `cccpass`

## Environment Variables
- `SERVER_URL` — Server URL (default: http://localhost:3111)
- `DB_PATH` — Database path for sql5 (default: box5.db)
- `SYNC_FOLDER` — Client sync folder (default: ./sync_folder)
- `SQL5_BINARY` — Path to sql5 binary (default: ~/.cache/sql5/sql5-macos-arm64)
- `DEFAULT_USER` / `DEFAULT_PASS` — k8s default credentials (default: ccc/cccpass)

## Project Structure
- `Server/` — FastAPI server with sql5 database
- `Client/` — Desktop sync client using watchdog
- `Website/` — Web UI with Jinja2 templates
- `tests/` — pytest tests (test_server.py, test_server_api.py, test_e2e.py)
- `k8s/` — Multi-tenant Docker version (port 8000)

## k8s Variant
- Uses `requirements.txt` (not pyproject.toml)
- Requires Docker running (`docker info` must succeed)
- Build image: `docker build -t box5-server:latest -f Dockerfile.box5 .`
- Start: `cd k8s && ./k8s_run.sh` (port 8000)
- Tests: `cd k8s && ./test.sh` (builds image if missing, then runs pytest)
- **SSH access:** `cd k8s && ./ccc_server.sh` — rebuilds image, starts server, creates container with SSH. Output shows `ssh ccc@localhost -p XXXXX` command.
- **SSH per user:** each container exposes port 22 as SSH. Get port from `k8s/uploads/{username}/.ssh_port`. API: `GET /api/ssh/{username}`.

## Testing
```bash
./test.sh                              # All tests (unit + API + E2E)
~/.venv/bin/python -m pytest tests/test_server.py -v       # Unit only
~/.venv/bin/python -m pytest tests/test_server_api.py -v   # API only
~/.venv/bin/python -m pytest tests/test_e2e.py -v          # E2E only (requires playwright)
```

E2E tests need `playwright install chromium` (done by install.sh). No lint/typecheck tools configured.

## Dev Rules
1. Write unit tests + system tests for all features
2. Create `test.sh` for project testing
3. Split into modules if code exceeds 1000 lines
4. Version planning docs: `_doc/v{x}.md` for each release, increment by 0.1
5. Code must compile/parse with no warnings (no lint/typecheck tools configured)

## Key Features
- **Public files:** put in `sync/public/` — accessible via `/api/public/files`
- **File view:** `.md` → Markdown, `.txt` → plain text, `.html` → static site, images → display, others → download
- **Editor:** `/editor` — Monaco + xterm.js terminal, WebSocket at `/ws/editor`
- **WebSocket protocol:** XML-wrapped JSON, types: `terminal_input/output`, `file_read/write/list`

## Documentation
- `README.md`, `Server/*.md`, `Client/*.md`, `Website/*.md`, `k8s/*.md`
- `tests/README.md`, `_doc/`, `_wiki/`

## Version Roadmap
- `_doc/v1.4-ssh.md` — SSH 多人連入（已完成）
- `_doc/v2.0.md` — 帳號安全（信箱驗證、密碼重置、API Key）
- `_doc/v2.1.md` — 管理後台
- `_doc/v2.2.md` — 分享功能
- `_doc/v2.3.md` — 監控備份
- `_doc/v2.4.md` — 進階安全（MFA）
- `_doc/v2.5.md` — 組織協作
- `_doc/v2.6.md` — 審計日誌
- `_doc/v2.7.md` — 使用者體驗優化