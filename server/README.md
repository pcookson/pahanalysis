# Server (FastAPI Backend)

This backend must use a local virtual environment at `server/.venv`.

## Setup (Required)

Do not use global `pip` or system-wide Python packages for this project.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (Development)

```bash
uvicorn app.main:app --reload --port 8000
```

## Health Check

After starting the server, verify:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```
