# box5

Dropbox-like app: Client (desktop sync) + Server (cloud storage) + Website (web UI).

## Tech Stack
- Python + FastAPI + sql5
- Development: uv (Python package manager)
- sql5 source: `/Users/Shared/ccc/project/sql5`

## Project Structure
- `Server/` — FastAPI server with sql5 database
- `Client/` — Desktop sync client using watchdog
- `Website/` — Web UI with Jinja2 templates
- `tests/` — pytest unit tests
- `_doc/` — planning docs and version notes

## Dev Rules (from plan.md)
1. Write unit tests + system tests for all features
2. Create `test.sh` for project testing
3. Split into modules if code exceeds 1000 lines
4. Version planning docs: `_doc/v{x}.md` for each release, increment by 0.1
5. Code must compile/parse with no warnings

## Install
```bash
./install.sh              # Install dependencies with uv
```

## Commands
```bash
./test.sh                 # Run all pytest tests
./run.sh                  # Run server, website, and client
uv run pytest tests/ -v    # Run tests with verbose output
```

## Server Commands
```bash
cd Server && uv run uvicorn main:app --reload --port 3111
```

## Client Commands
```bash
uv run python -m Client.main --username USER --password PASS --folder ./sync
```

## Website Commands
```bash
cd Website && uv run uvicorn main:app --reload --port 3112
```

## Environment Variables
- `SERVER_URL` — Server URL (default: http://localhost:3111)
- `DB_PATH` — Database path for sql5 (default: box5.db)
- `SYNC_FOLDER` — Client sync folder (default: ./sync_folder)
- `SQL5_BINARY` — Path to sql5 binary (default: ~/.cache/sql5/sql5-macos-arm64)

## Public Folder Feature
- Put files in `sync/public/` to upload them as public (accessible without login)
- Public files available via `GET /api/public/files`
- Private files go in `sync/`
- `is_public` parameter in upload API accepts "true"/"false" string

## Folder Navigation
- Website shows files in current folder only
- Click subfolder to navigate into it
- Breadcrumb shows current path
- Folder stored in database, uploaded with file

## File View/Download
- `.md` files: Render as Markdown (bold, headers, lists, code blocks)
- `.txt` files: Display as plain text in `<pre>` block
- `.html` files: Render directly as HTML
- `.jpg`/`.jpeg`/`.png`/`.gif`/`.webp`: Display as image
- Other files: Redirect to download

## Editor Feature (v0.5)
- Web-based code editor similar to VSCode
- Access at `/editor` route (default path: ./sync)
- Monaco Editor for code editing
- Integrated terminal with xterm.js
- File explorer sidebar (right side)
- Tab-based file editing
- HTTP API endpoints: `/api/editor/files`, `/api/editor/file`
- Terminal: type command and press Enter to execute

## WebSocket Protocol
- Endpoint: `/ws/editor`
- Message format: XML with JSON payload
- Types: `terminal_input`, `terminal_output`, `file_read`, `file_write`, `file_list`

## Testing
```bash
./test.sh                 # Run all tests (unit + API + E2E)
python -m pytest tests/ -v  # Run all tests with verbose output
python -m pytest tests/test_server_api.py -v  # Server API tests only
python -m pytest tests/test_e2e.py -v  # E2E tests only
```

## Version History
- v0.7: Added menu bar (File/Edit/View/Help), keyboard shortcuts, modified file indicator
- v0.6: Fixed Terminal WebSocket 403 issue, added terminal with command prompt
- v0.5: Web-based code editor (Monaco Editor + xterm.js), HTTP API for file operations
- v0.4: UV migration (pyproject.toml, uv run), cross-platform path fixes, test infrastructure improvements
- v0.3: Automated testing (Server API + Playwright E2E) - 37 tests total
- v0.2: Bug fixes (TemplateResponse API, sql5 binary path), .html view support
- v0.1: Initial release with basic features