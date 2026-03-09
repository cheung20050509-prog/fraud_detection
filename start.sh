#!/usr/bin/env bash

set -euo pipefail

# 电信诈骗风险阻断系统 - 一键启动脚本（Linux）

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

HOST="${HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
CLOUDFLARED_PROTOCOL="http2"

BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/health"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
CLOUDFLARED_TARGET_URL="${FRONTEND_URL}"

BACKEND_PID=""
FRONTEND_PID=""
CLOUDFLARED_PID=""
CLOUDFLARED_LOG=""
PUBLIC_TUNNEL_URL=""
CLEANUP_DONE="false"
PRESERVE_SERVICES_ON_EXIT="false"

resolve_python_bin() {
    if [[ -n "${PYTHON_BIN:-}" && -x "${PYTHON_BIN}" ]]; then
        echo "${PYTHON_BIN}"
        return
    fi

    if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
        echo "${CONDA_PREFIX}/bin/python"
        return
    fi

    if [[ -x "/root/autodl-tmp/fraud_detection/bin/python" ]]; then
        echo "/root/autodl-tmp/fraud_detection/bin/python"
        return
    fi

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return
    fi

    if command -v python >/dev/null 2>&1; then
        command -v python
        return
    fi

    echo ""
}

resolve_node_bin() {
    if [[ -n "${NODE_BIN:-}" && -x "${NODE_BIN}" ]]; then
        echo "${NODE_BIN}"
        return
    fi

    if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/node" ]]; then
        echo "${CONDA_PREFIX}/bin/node"
        return
    fi

    if command -v node >/dev/null 2>&1; then
        command -v node
        return
    fi

    echo ""
}

resolve_npm_bin() {
    if [[ -n "${NPM_BIN:-}" && -x "${NPM_BIN}" ]]; then
        echo "${NPM_BIN}"
        return
    fi

    if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/npm" ]]; then
        echo "${CONDA_PREFIX}/bin/npm"
        return
    fi

    if command -v npm >/dev/null 2>&1; then
        command -v npm
        return
    fi

    echo ""
}

resolve_cloudflared_bin() {
    if [[ -n "${CLOUDFLARED_BIN:-}" && -x "${CLOUDFLARED_BIN}" ]]; then
        echo "${CLOUDFLARED_BIN}"
        return
    fi

    if [[ -x "/root/autodl-tmp/cloudflared" ]]; then
        echo "/root/autodl-tmp/cloudflared"
        return
    fi

    if command -v cloudflared >/dev/null 2>&1; then
        command -v cloudflared
        return
    fi

    echo ""
}

wait_tunnel_url() {
    local log_file="$1"
    local pid="$2"
    local retries="${3:-30}"
    local url=""

    for ((i=1; i<=retries; i++)); do
        if [[ -f "${log_file}" ]]; then
            url="$(grep -oE 'https://[-[:alnum:]]+\.trycloudflare\.com' "${log_file}" | tail -n 1 || true)"
            if [[ -n "${url}" ]]; then
                echo "${url}"
                return 0
            fi
        fi

        if ! kill -0 "${pid}" >/dev/null 2>&1; then
            break
        fi

        sleep 1
    done

    return 1
}

wait_http() {
    local url="$1"
    local label="$2"
    local retries="${3:-45}"

    for ((i=1; i<=retries; i++)); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo "✅ ${label} 就绪: ${url}"
            return 0
        fi
        sleep 1
    done

    echo "❌ ${label} 未在预期时间内就绪: ${url}"
    return 1
}

launch_service() {
    local pid_var="$1"
    local workdir="$2"
    local log_file="$3"
    shift 3

    local previous_dir="${PWD}"
    cd "${workdir}"
    nohup "$@" >"${log_file}" 2>&1 &
    eval "${pid_var}=$!"
    cd "${previous_dir}"
}

cleanup() {
    if [[ "${CLEANUP_DONE}" == "true" ]]; then
        return 0
    fi
    CLEANUP_DONE="true"

    if [[ "${PRESERVE_SERVICES_ON_EXIT}" == "true" ]]; then
        return 0
    fi

    echo ""
    echo "🛑 正在停止服务..."

    if [[ -n "${BACKEND_PID}" ]]; then
        kill "${BACKEND_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${FRONTEND_PID}" ]]; then
        kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${CLOUDFLARED_PID}" ]]; then
        kill "${CLOUDFLARED_PID}" >/dev/null 2>&1 || true
    fi

    wait >/dev/null 2>&1 || true
    echo "✅ 服务已停止"
}

trap cleanup INT TERM EXIT

PYTHON_BIN="$(resolve_python_bin)"
NODE_BIN="$(resolve_node_bin)"
NPM_BIN="$(resolve_npm_bin)"
CLOUDFLARED_BIN_PATH="$(resolve_cloudflared_bin)"

# Ensure npm scripts can locate node when only conda-local binaries are available.
if [[ -n "${NODE_BIN}" ]]; then
    export PATH="$(dirname "${NODE_BIN}"):${PATH}"
fi

echo "🚀 启动电信诈骗风险阻断系统..."
echo "=================================="

if [[ -z "${PYTHON_BIN}" ]]; then
    echo "❌ 未找到可用 Python，请先激活环境（例如 conda activate fraud_detection）"
    exit 1
fi

if [[ -z "${NODE_BIN}" || -z "${NPM_BIN}" ]]; then
    echo "❌ 未找到可用 Node.js/npm，请先激活包含 node/npm 的环境"
    exit 1
fi

echo "✅ Python: ${PYTHON_BIN} ($(${PYTHON_BIN} --version 2>&1))"
echo "✅ Node: ${NODE_BIN} ($(${NODE_BIN} --version 2>&1))"
echo "✅ NPM: ${NPM_BIN} ($(${NPM_BIN} --version 2>&1))"

if [[ -n "${CLOUDFLARED_BIN_PATH}" ]]; then
    echo "✅ cloudflared: ${CLOUDFLARED_BIN_PATH} ($(${CLOUDFLARED_BIN_PATH} --version 2>&1 | head -n 1))"
else
    echo "ℹ️ cloudflared: 未找到"
fi

# 默认严格模式：依赖缺失时返回显式错误，不做静默降级。
export STRICT_NO_FALLBACK="${STRICT_NO_FALLBACK:-true}"
echo "🔧 STRICT_NO_FALLBACK=${STRICT_NO_FALLBACK}"

echo ""
echo "🔍 检查后端关键依赖..."
if ! "${PYTHON_BIN}" - <<'PY'
import importlib.util
modules = ["fastapi", "uvicorn", "sqlalchemy", "aiofiles"]
missing = [m for m in modules if importlib.util.find_spec(m) is None]
if missing:
        raise SystemExit("缺少Python依赖: " + ", ".join(missing))
PY
then
    echo "❌ 后端依赖不完整，请先安装:"
    echo "   ${PYTHON_BIN} -m pip install -r ${BACKEND_DIR}/requirements.txt"
    exit 1
fi

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
    echo "📦 前端依赖缺失，开始安装..."
    (cd "${FRONTEND_DIR}" && "${NPM_BIN}" install)
fi

mkdir -p "${BACKEND_DIR}/logs" "${FRONTEND_DIR}/.logs"
BACKEND_LOG="${BACKEND_DIR}/logs/dev-backend.log"
FRONTEND_LOG="${FRONTEND_DIR}/.logs/dev-frontend.log"

echo ""
echo "🖥 启动后端服务..."
launch_service BACKEND_PID "${BACKEND_DIR}" "${BACKEND_LOG}" "${PYTHON_BIN}" -m uvicorn app.main:app --host "${HOST}" --port "${BACKEND_PORT}"

echo "🌐 启动前端服务..."
launch_service FRONTEND_PID "${FRONTEND_DIR}" "${FRONTEND_LOG}" "${NODE_BIN}" ./node_modules/vite/bin/vite.js --host "${HOST}" --port "${FRONTEND_PORT}"

if ! wait_http "${BACKEND_HEALTH_URL}" "后端健康检查" 45; then
    echo "---- 后端日志（最后80行） ----"
    tail -n 80 "${BACKEND_LOG}" || true
    exit 1
fi

if ! wait_http "${FRONTEND_URL}" "前端首页" 45; then
    echo "---- 前端日志（最后80行） ----"
    tail -n 80 "${FRONTEND_LOG}" || true
    exit 1
fi

if [[ -n "${CLOUDFLARED_BIN_PATH}" ]]; then
    CLOUDFLARED_LOG="${FRONTEND_DIR}/.logs/cloudflared-quick-tunnel.log"

    echo ""
    echo "🌍 启动 Cloudflare Quick Tunnel..."
    launch_service CLOUDFLARED_PID "${ROOT_DIR}" "${CLOUDFLARED_LOG}" "${CLOUDFLARED_BIN_PATH}" tunnel --protocol "${CLOUDFLARED_PROTOCOL}" --url "${CLOUDFLARED_TARGET_URL}"

    if PUBLIC_TUNNEL_URL="$(wait_tunnel_url "${CLOUDFLARED_LOG}" "${CLOUDFLARED_PID}" 30)"; then
        :
    else
        PUBLIC_TUNNEL_URL=""
        echo "⚠️ Cloudflare Quick Tunnel 未在预期时间内返回公网地址"
        echo "---- Cloudflare 日志（最后40行） ----"
        tail -n 40 "${CLOUDFLARED_LOG}" || true
    fi
else
    echo ""
    echo "ℹ️ 跳过 Cloudflare Quick Tunnel：未检测到 cloudflared"
fi

echo ""
echo "🎉 系统启动完成"
echo "=================================="
echo "📱 前端地址: ${FRONTEND_URL}"
echo "🔧 后端API: http://127.0.0.1:${BACKEND_PORT}"
echo "📡 API文档: http://127.0.0.1:${BACKEND_PORT}/docs"
echo "📡 健康检查: ${BACKEND_HEALTH_URL}"
echo ""
echo "🎯 主要页面"
echo "   - AI陪练: ${FRONTEND_URL}/practice"
echo "   - 实时监护: ${FRONTEND_URL}/monitor"
echo "   - 案例分析: ${FRONTEND_URL}/analysis"
echo ""
echo "📄 日志文件"
echo "   - 后端: ${BACKEND_LOG}"
echo "   - 前端: ${FRONTEND_LOG}"
if [[ -n "${CLOUDFLARED_LOG}" ]]; then
    echo "   - Tunnel: ${CLOUDFLARED_LOG}"
fi
if [[ -n "${PUBLIC_TUNNEL_URL}" ]]; then
    echo ""
    echo "🌍 公网访问地址: ${PUBLIC_TUNNEL_URL}"
fi
echo ""
echo "💡 严格模式说明"
echo "   - 当前默认 STRICT_NO_FALLBACK=true"
echo "   - 若 torch/transformers/whisper 等依赖缺失，监护/音频分析会返回明确错误"
if [[ -z "${CLOUDFLARED_BIN_PATH}" ]]; then
    echo "   - 未检测到 cloudflared，未启用公网隧道"
else
    echo "   - Cloudflare Quick Tunnel 目标: ${CLOUDFLARED_TARGET_URL}"
fi
echo ""

echo "📦 服务已通过 nohup 转入后台运行"
echo "   - 现在可以安全断开 SSH"
echo "   - 停止服务: bash ${ROOT_DIR}/stop.sh"
echo "   - 查看后端日志: tail -f ${BACKEND_LOG}"
echo "   - 查看前端日志: tail -f ${FRONTEND_LOG}"
if [[ -n "${CLOUDFLARED_LOG}" ]]; then
    echo "   - 查看 Tunnel 日志: tail -f ${CLOUDFLARED_LOG}"
fi
echo "=================================="

PRESERVE_SERVICES_ON_EXIT="true"
exit 0