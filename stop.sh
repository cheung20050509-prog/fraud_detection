#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

collect_port_pids() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
        return
    fi

    if command -v ss >/dev/null 2>&1; then
        ss -ltnp "sport = :${port}" 2>/dev/null \
            | grep -oE 'pid=[0-9]+' \
            | cut -d= -f2 \
            | sort -u \
            || true
        return
    fi

    if command -v fuser >/dev/null 2>&1; then
        fuser -n tcp "${port}" 2>/dev/null \
            | tr ' ' '\n' \
            | sed '/^$/d' \
            | sort -u \
            || true
        return
    fi
}

collect_pattern_pids() {
    local pattern="$1"
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -f "${pattern}" 2>/dev/null || true
    fi
}

merge_unique_pids() {
    sed '/^$/d' | sort -u
}

is_alive() {
    local pid="$1"
    kill -0 "${pid}" >/dev/null 2>&1
}

stop_pid_gracefully() {
    local pid="$1"
    local grace_seconds="${2:-5}"

    if ! is_alive "${pid}"; then
        return 0
    fi

    kill "${pid}" >/dev/null 2>&1 || true

    local i
    for ((i=0; i<grace_seconds; i++)); do
        if ! is_alive "${pid}"; then
            return 0
        fi
        sleep 1
    done

    if is_alive "${pid}"; then
        kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
}

main() {
    echo "Stopping fraud-blocking-system services..."

    local pids
    pids="$({
        collect_port_pids "${BACKEND_PORT}"
        collect_port_pids "${FRONTEND_PORT}"

        # Fallback patterns in case ports changed or process is still starting.
        collect_pattern_pids 'uvicorn app.main:app'
        collect_pattern_pids 'node .*vite/bin/vite.js'
        collect_pattern_pids 'cloudflared tunnel --protocol '
    } | merge_unique_pids)"

    if [[ -z "${pids}" ]]; then
        echo "No running backend/frontend process found."
        exit 0
    fi

    local pid
    while IFS= read -r pid; do
        [[ -z "${pid}" ]] && continue

        local cmd
        cmd="$(ps -p "${pid}" -o args= 2>/dev/null || true)"
        if [[ -n "${cmd}" ]]; then
            echo "Stopping PID ${pid}: ${cmd}"
        else
            echo "Stopping PID ${pid}"
        fi

        stop_pid_gracefully "${pid}" 5
    done <<< "${pids}"

    # Double-check ports after shutdown.
    local backend_left
    local frontend_left
    backend_left="$(collect_port_pids "${BACKEND_PORT}" | merge_unique_pids || true)"
    frontend_left="$(collect_port_pids "${FRONTEND_PORT}" | merge_unique_pids || true)"

    if [[ -n "${backend_left}" || -n "${frontend_left}" ]]; then
        echo "Warning: some processes are still listening."
        [[ -n "${backend_left}" ]] && echo "  backend port ${BACKEND_PORT}: ${backend_left}"
        [[ -n "${frontend_left}" ]] && echo "  frontend port ${FRONTEND_PORT}: ${frontend_left}"
        exit 1
    fi

    echo "Services stopped."
}

main "$@"
