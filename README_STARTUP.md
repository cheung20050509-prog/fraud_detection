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

- Starts the FastAPI backend first
- Starts the FastAPI backend on port `8000`
- Starts the Vite frontend next on port `5173`
- Checks backend health and frontend reachability
- Automatically starts a Cloudflare Quick Tunnel last if `cloudflared` is available
- Prints log file locations and then exits while services continue running via `nohup`

If `cloudflared` exists at `/root/autodl-tmp/cloudflared` or in `PATH`, `start.sh` will automatically create a Quick Tunnel for the frontend and print the public URL.

After startup finishes, the script exits by itself. Backend, frontend, and tunnel processes keep running in the background, so you can disconnect SSH safely.

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

You can also stop services from another shell:

```bash
cd /root/autodl-tmp/fraud-blocking-system
bash stop.sh
```

`stop.sh` will also try to stop the Quick Tunnel process started for this project.

## Remote Access

If the project is running on a remote Linux machine, do not open the remote machine's `127.0.0.1` directly in your local browser.

Forward these ports to your local machine first:

- `5173` for the frontend
- `8000` for the backend

After port forwarding, open local URLs such as `http://127.0.0.1:5173`.

## AutoDL Quick Tunnel

If you are running on AutoDL or another hosted environment where direct inbound access is inconvenient, use Cloudflare Quick Tunnel.

The frontend dev server already proxies `/api` and `/ws` to the backend, so exposing `5173` is usually enough for the whole app.

### Install `cloudflared`

```bash
cd /root/autodl-tmp
wget -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
./cloudflared --version
```

### Expose the frontend

```bash
cd /root/autodl-tmp
./cloudflared tunnel --protocol http2 --url http://127.0.0.1:5173
```

If you already use `bash start.sh`, you usually do not need to run this command manually because the script can do it automatically.

Why `--protocol http2`:

- Some hosted environments block or degrade QUIC/UDP
- `http2` is usually more stable on AutoDL

After startup, `cloudflared` prints a temporary public URL like:

```text
https://example-name.trycloudflare.com
```

Open that URL in your local browser.

### Optional: Expose backend docs separately

```bash
cd /root/autodl-tmp
./cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000
```

### Notes

- Quick Tunnel is free and suitable for development/testing
- The URL is temporary and changes when you restart the tunnel
- Keep the `cloudflared` process running, or the public URL will stop working
- The frontend Vite config already allows `*.trycloudflare.com` hosts

## Common Problems

### `node: No such file or directory`

You did not activate the `fraud_detection` environment before starting the frontend.

```bash
conda activate fraud_detection
```

### `npm: command not found`

Same root cause as above. `npm` is expected to come from the conda environment.

### `Blocked request. This host is not allowed.`

If you see this when using Cloudflare Quick Tunnel, make sure you are using the updated Vite config that allows `*.trycloudflare.com`.

If you need to allow more custom hosts, set:

```bash
VITE_ALLOWED_HOSTS=host1.example.com,host2.example.com
```

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