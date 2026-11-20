#!/usr/bin/env bash
# =============================================================================
# Safe, Isolated Docker Deployment Script for AksharaMitra (SHR Trinity)
# Host Directory: /opt/shrtrinity/aksharamitra
# Host Port:      127.0.0.1:8510 -> Container Port 8501
# Target Domain:  https://aksharamitra.shrtrinity.com
#
# SAFETY GUARANTEES:
# - Never touches, stops, or restarts FinPilot AI or unrelated services
# - Never modifies DNS records or overwrites existing databases
# - Checks available RAM, disk space, and port 8510 before building
# =============================================================================
set -euo pipefail

APP_DIR="/opt/shrtrinity/aksharamitra"
APP_PORT="8510"
CONTAINER_NAME="shr_aksharamitra_app"

echo "========================================================================"
echo "  AksharaMitra (SHR Trinity) – Safe Docker Deployment"
echo "========================================================================"

echo ""
echo "[1/6] Inspecting VPS resources (RAM, Disk, Port ${APP_PORT})..."
free -h || true
df -h / || true

if ss -tuln | grep -q ":${APP_PORT} "; then
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "OK: Port ${APP_PORT} is currently used by existing ${CONTAINER_NAME} (will refresh cleanly)."
    else
        echo "ERROR: Port ${APP_PORT} is already in use by another process! Aborting to protect existing services."
        exit 1
    fi
else
    echo "OK: Port ${APP_PORT} is free."
fi

echo ""
echo "[2/6] Verifying isolated application directory (${APP_DIR})..."
if [ ! -d "${APP_DIR}" ]; then
    echo "ERROR: Directory ${APP_DIR} does not exist. Clone the repository into ${APP_DIR} first."
    exit 1
fi
cd "${APP_DIR}"

echo ""
echo "[3/6] Ensuring persistent data directories and SQLite database exist..."
mkdir -p "${APP_DIR}/data" "${APP_DIR}/kb_cache" "${APP_DIR}/pdfs" "${APP_DIR}/.streamlit"
if [ ! -f "${APP_DIR}/users.db" ]; then
    touch "${APP_DIR}/users.db"
fi
chmod 755 "${APP_DIR}/data" "${APP_DIR}/kb_cache" "${APP_DIR}/pdfs"

if [ ! -f "${APP_DIR}/.streamlit/secrets.toml" ]; then
    echo "WARNING: ${APP_DIR}/.streamlit/secrets.toml not found."
    echo "         Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and add your API keys if needed."
fi

echo ""
echo "[4/6] Building and starting AksharaMitra Docker container..."
docker compose up -d --build

echo ""
echo "[5/6] Waiting for container healthcheck on http://127.0.0.1:${APP_PORT}/_stcore/health..."
for i in $(seq 1 15); do
    if curl -fsS "http://127.0.0.1:${APP_PORT}/_stcore/health" >/dev/null 2>&1; then
        echo "SUCCESS: AksharaMitra is healthy on http://127.0.0.1:${APP_PORT}!"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "ERROR: AksharaMitra did not pass healthcheck within 30 seconds."
        docker compose logs --tail=40
        exit 1
    fi
    sleep 2
done

echo ""
echo "[6/6] Deployment complete! Container status:"
docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Next (if not yet configured): Enable Nginx site and run Certbot for https://aksharamitra.shrtrinity.com"
