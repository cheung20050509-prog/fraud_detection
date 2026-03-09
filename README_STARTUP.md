# Fraud Blocking System Startup Guide

This guide is the shortest reliable way to start the project locally on the current machine.

## Prerequisite

Activate the conda environment first. This step matters because both Python and Node.js tools are available in this environment.

```bash
conda activate fraud_detection
```

If `conda activate` is not available in your shell yet, initialize conda first:

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate fraud_detection
```

## Recommended: One-Click Start

From the project root, run:

```bash
cd /root/autodl-tmp/fraud-blocking-system
bash start.sh
```

What this does:

- Starts the FastAPI backend on port `8000`
- Starts the Vite frontend on port `5173`
- Checks backend health and frontend reachability
- Prints log file locations

## Manual Start

Use this if you want backend and frontend in separate terminals.

### Terminal 1: Backend

```bash
conda activate fraud_detection
cd /root/autodl-tmp/fraud-blocking-system/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend

```bash
conda activate fraud_detection
cd /root/autodl-tmp/fraud-blocking-system/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

## Access URLs

After startup, use these addresses:

- Frontend home: `http://127.0.0.1:5173`
- AI practice: `http://127.0.0.1:5173/practice`
- Real-time monitor: `http://127.0.0.1:5173/monitor`
- Case analysis: `http://127.0.0.1:5173/analysis`
- Backend health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

## Stop Services

If you started everything with `bash start.sh`, press `Ctrl+C` in that terminal.

You can also stop services from another shell:

```bash
cd /root/autodl-tmp/fraud-blocking-system
bash stop.sh
```

## Remote Access

If the project is running on a remote Linux machine, do not open the remote machine's `127.0.0.1` directly in your local browser.

Forward these ports to your local machine first:

- `5173` for the frontend
- `8000` for the backend

After port forwarding, open local URLs such as `http://127.0.0.1:5173`.

## Common Problems

### `node: No such file or directory`

You did not activate the `fraud_detection` environment before starting the frontend.

```bash
conda activate fraud_detection
```

### `npm: command not found`

Same root cause as above. `npm` is expected to come from the conda environment.

### Backend health check fails

Check whether port `8000` is already occupied or whether backend dependencies are missing:

```bash
cd /root/autodl-tmp/fraud-blocking-system/backend
python -m pip install -r requirements.txt
```

### Frontend dependencies missing

Install them once:

```bash
cd /root/autodl-tmp/fraud-blocking-system/frontend
npm install
```

## Logs

If you use `bash start.sh`, logs are written to:

- `backend/logs/dev-backend.log`
- `frontend/.logs/dev-frontend.log`

## Quick Check

After startup, these two commands should succeed:

```bash
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:5173
```