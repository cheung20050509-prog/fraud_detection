# Fraud Blocking System

## Overview
Fraud Blocking System provides three core workflows:
- `/practice`: AI conversation practice against scam scenarios.
- `/monitor`: real-time monitoring over WebSocket audio stream.
- `/analysis`: offline file upload and fraud-risk analysis pipeline.

The backend is FastAPI and the frontend is Vue 3 + Vite.

## One-Click Start (Linux)
### 1. Activate environment
```bash
conda activate /root/autodl-tmp/fraud_detection
```

### 2. Start services
```bash
cd /root/autodl-tmp/fraud-blocking-system
bash start.sh
```

### 3. Open pages
- Frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## What `start.sh` does
- Detects usable Python/Node/npm from current environment.
- Verifies backend critical dependencies.
- Installs frontend dependencies if missing.
- Starts backend (`uvicorn`) and frontend (`vite`) together.
- Waits for health checks and prints access URLs/log paths.
- Stops both services on `Ctrl+C`.

## Strict Mode Policy
Strict mode is enabled by default:
- `STRICT_NO_FALLBACK=true`
- Missing core AI dependencies (such as `torch`, `transformers`, `whisper`) do not silently downgrade.
- Instead, monitoring/audio analysis returns explicit errors.

If you need to temporarily disable strict mode:
```bash
STRICT_NO_FALLBACK=false bash start.sh
```

## Quick Integration Smoke Test
After services are up:
```bash
cd /root/autodl-tmp/fraud-blocking-system
/root/autodl-tmp/fraud_detection/bin/python scripts/smoke_test.py
```

This checks:
- `/analysis` page reachability
- upload -> poll analysis result flow
- `/monitor` WebSocket message flow

## Troubleshooting
### `No module named 'torch'` or `transformers`
Install backend dependencies in your active environment:
```bash
cd /root/autodl-tmp/fraud-blocking-system/backend
/root/autodl-tmp/fraud_detection/bin/python -m pip install -r requirements.txt
```

### `npm: command not found`
Ensure your env includes Node/npm, or provide explicit binaries:
```bash
NODE_BIN=/path/to/node NPM_BIN=/path/to/npm bash start.sh
```

### Frontend build script permission issue (`vue-tsc: Permission denied`)
Use Node to invoke tools directly:
```bash
cd /root/autodl-tmp/fraud-blocking-system/frontend
/root/autodl-tmp/conda-envs/fraud_detection/bin/node ./node_modules/vue-tsc/bin/vue-tsc.js --noEmit
/root/autodl-tmp/conda-envs/fraud_detection/bin/node ./node_modules/vite/bin/vite.js build
```
