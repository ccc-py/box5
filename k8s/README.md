# Box5 with Docker Isolation (k8s)

A file management website where each user runs their own isolated Docker container with box5.

## Features

- User registration with automatic Docker container creation
- Each user gets a personal Docker container running box5
- Secure isolation between users
- File management (upload, download, view, edit)
- Markdown rendering with path headers
- Web editor with Monaco Editor + terminal
- Terminal: WebSocket-based zsh shell with xterm.js

## Quick Start

```bash
# Build Docker image (first time)
docker build -t box5-server:latest -f Dockerfile.box5 .

# Start k8s server
cd /Users/Shared/ccc/project/box5/k8s
./k8s_run.sh
```

Website: http://localhost:8000
- Login: http://localhost:8000/login
- Editor: http://localhost:8000/editor

Default user: `ccc` / `cccpass`

## Architecture

- **Main Web Server** (port 8000): Handles user authentication and website UI
- **Docker Manager**: Creates/manages isolated containers for each user
- **User Containers**: Each user's personal box5 instance (port 3111)
- **Volume Mount**: `uploads/{username}/sync` → `/tmp/box5/sync`
- **WebSocket**: `/ws/editor` for terminal communication

## File Viewing

| Type | Display |
|------|---------|
| `.md` | Markdown rendered |
| `.html` | Direct HTML |
| Images (jpg, png, gif, webp, svg, pdf) | Direct display |
| Code (py, js, ts, sh, c, go, rs...) | Code block with path header |
| `.txt` | Plain text |

## Testing

```bash
./test.sh
```

- Unit tests: 19 passed
- E2E tests: 14 passed  
- WebSocket terminal tests: 2 passed