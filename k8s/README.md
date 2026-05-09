# Box5 with Docker Isolation

A file management website where each user runs their own isolated Docker container with box5.

## Features

- User registration with automatic Docker container creation
- Each user gets a personal Docker container running box5
- Secure isolation between users
- File management (upload, download, view, edit)
- Markdown rendering
- Editor with real-time collaboration

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p uploads containers

# Run the application
python main.py
```

The website will be available at http://localhost:8000

## Architecture

- **Main Web Server**: Handles user authentication and website UI
- **Docker Manager**: Creates/manages isolated containers for each user
- **User Containers**: Each user's personal box5 instance runs in Docker