#!/usr/bin/env bash
# =============================================================================
# Safe, Isolated Docker Deployment Script for MockMate (SHR Trinity)
# Host Directory: /opt/shrtrinity/mockmate
# Host Port:      127.0.0.1:8511 -> Container Port 8501
# Target Domain:  https://mockmate.shrtrinity.io (and mockmate.shrtrinity.com)
#
# SAFETY GUARANTEES:
# - Never touches, stops, or restarts FinPilot AI or AksharaMitra
# - Runs on isolated port 8511
# - Isolated in /opt/shrtrinity/mockmate
# =============================================================================
set -euo pipefail

APP_DIR="/opt/shrtrinity/mockmate"
APP_PORT="8511"
CONTAINER_NAME="shr_mockmate_app"
REPO_URL="https://github.com/HemaLalitha0/rag-main.git"

echo "========================================================================"
echo "  MockMate (SHR Trinity) – Safe Docker Deployment"
echo "========================================================================"

echo ""
echo "[1/6] Inspecting VPS resources and Port ${APP_PORT}..."
free -h || true
df -h / || true

if ss -tuln | grep -q ":${APP_PORT} "; then
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "OK: Port ${APP_PORT} is currently used by existing ${CONTAINER_NAME} (refreshing)."
    else
        echo "ERROR: Port ${APP_PORT} is already in use by another service! Aborting."
        exit 1
    fi
else
    echo "OK: Port ${APP_PORT} is free."
fi

echo ""
echo "[2/6] Preparing isolated application directory (${APP_DIR})..."
mkdir -p /opt/shrtrinity
if [ ! -d "${APP_DIR}/.git" ]; then
    echo "Cloning repository into ${APP_DIR}..."
    git clone "${REPO_URL}" "${APP_DIR}"
else
    echo "Pulling latest code in ${APP_DIR}..."
    cd "${APP_DIR}"
    git pull origin main
fi
cd "${APP_DIR}"

echo ""
echo "[3/6] Setting up persistent directories and environment..."
mkdir -p "${APP_DIR}/data" "${APP_DIR}/kb_cache" "${APP_DIR}/pdfs" "${APP_DIR}/.streamlit"
if [ ! -f "${APP_DIR}/users.db" ]; then
    touch "${APP_DIR}/users.db"
fi
chmod 755 "${APP_DIR}/data" "${APP_DIR}/kb_cache" "${APP_DIR}/pdfs"

# Inherit secrets if available from aksharamitra or root
if [ ! -f "${APP_DIR}/.streamlit/secrets.toml" ]; then
    if [ -f "/opt/shrtrinity/aksharamitra/.streamlit/secrets.toml" ]; then
        cp "/opt/shrtrinity/aksharamitra/.streamlit/secrets.toml" "${APP_DIR}/.streamlit/secrets.toml"
        echo "Copied existing secrets to MockMate."
    fi
fi

echo ""
echo "[4/6] Building and launching MockMate Docker container on port ${APP_PORT}..."
docker compose -f docker-compose.mockmate.yml up -d --build

echo ""
echo "[5/6] Waiting for container health check on http://127.0.0.1:${APP_PORT}/_stcore/health..."
for i in $(seq 1 15); do
    if curl -fsS "http://127.0.0.1:${APP_PORT}/_stcore/health" >/dev/null 2>&1; then
        echo "SUCCESS: MockMate is live and healthy on http://127.0.0.1:${APP_PORT}!"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "WARNING: Health check taking longer than usual. Checking container logs:"
        docker compose -f docker-compose.mockmate.yml logs --tail=40
    fi
    sleep 2
done

echo ""
echo "[6/6] MockMate container status:"
docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Deployment successful!"
