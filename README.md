# JWST Spectrum Viewer Monorepo

Monorepo scaffold for a JWST Spectrum Viewer web application.

## Repository Layout

- `server/` - Python backend service (uses a local virtual environment at `server/.venv`)
- `web/` - Frontend application
- `Makefile` - Developer workflow commands

## Python Isolation (Required on Unix)

On Unix systems (Linux/macOS), using system Python or global `pip` can break other projects and can conflict with OS-managed packages.

Rules for this repo:

- Do **NOT** use system Python packages for project dependencies
- Always create and activate `server/.venv`
- Never use global `pip`
- Install dependencies only after activating the local virtual environment

Why this matters:

- Prevents version conflicts between projects
- Avoids accidentally modifying OS or user-wide Python environments
- Makes onboarding and reproducing the backend environment predictable

## Backend Setup (Manual)

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Makefile Workflow

- `make setup` - Create `server/.venv` if missing and install backend dependencies
- `make dev` - Start backend and frontend dev servers (uses the backend venv Python)
- `make clean` - Remove virtualenv, caches, and optional frontend artifacts

## Docker (Easy Share / Deploy Path)

This repo now includes a simple Docker Compose setup:

- `server` service: FastAPI backend
- `web` service: static frontend served by Nginx, with `/api` proxied to the backend
- `./data` volume mount: reserved for persistent app data (including a future SQLite DB)

Run it:

```bash
docker compose up --build
```

Then open `http://localhost:8080`.

Notes:

- Future SQLite path is already reserved via `SQLITE_DB_PATH=/data/app.db`
- JWST cache is configured to persist under `/data/jwst-cache`
- Frontend API calls now support `VITE_API_BASE_URL` and default to same-origin (works behind the Nginx proxy)

## Notes

- `make dev` serves a simple static placeholder from `web/` until the frontend toolchain is added.
- The backend and frontend commands can be customized in `Makefile` variables later as the apps are implemented.
