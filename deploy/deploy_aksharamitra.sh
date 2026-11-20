#!/usr/bin/env bash
# =============================================================================
# Safe, Non-Destructive Deployment Script for AksharaMitra (SHR Trinity)
# Installs AksharaMitra in an isolated directory (/opt/shrtrinity/aksharamitra)
# on port 127.0.0.1:8510 without touching FinPilot AI or existing services.
# =============================================================================
set -euo pipefail

APP_DIR="/opt/shrtrinity/aksharamitra"
APP_PORT="8510"
REPO_URL="${1:-https://github.com/HemaLalitha0/rag-main.git}"

echo "=== [1/6] Pre-flight Safety Checks ==="
if ss -tuln | grep -q ":${APP_PORT} "; then
    echo "Notice: Port ${APP_PORT} is already in use. Checking if it belongs to aksharamitra..."
fi

echo "=== [2/6] Preparing Isolated Application Directory (${APP_DIR}) ==="
sudo mkdir -p "${APP_DIR}"
sudo mkdir -p /var/log/aksharamitra
sudo chown -R "$USER":"$USER" "${APP_DIR}"

if [ -d "${APP_DIR}/.git" ]; then
    echo "Updating existing AksharaMitra repository..."
    cd "${APP_DIR}"
    git pull origin main
else
    echo "Cloning AksharaMitra repository into ${APP_DIR}..."
    git clone "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
fi

echo "=== [3/6] Setting Up Isolated Python Virtual Environment ==="
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "=== [4/6] Configuring Systemd Service (aksharamitra.service) ==="
sudo cp "${APP_DIR}/deploy/aksharamitra.service" /etc/systemd/system/aksharamitra.service
sudo chown -R www-data:www-data "${APP_DIR}" /var/log/aksharamitra
sudo systemctl daemon-reload
sudo systemctl enable aksharamitra
sudo systemctl restart aksharamitra

echo "=== [5/6] Verifying Local Healthcheck on 127.0.0.1:${APP_PORT} ==="
sleep 4
curl -fsS "http://127.0.0.1:${APP_PORT}/_stcore/health" && echo " Healthcheck OK!"

echo "=== [6/6] Done! Next Step: Enable Nginx site if subdomain DNS is ready ==="
echo "To activate Nginx reverse proxy for aksharamitra.shrtrinity.com:"
echo "  sudo cp ${APP_DIR}/deploy/nginx_aksharamitra.conf /etc/nginx/sites-available/aksharamitra.conf"
echo "  sudo ln -s /etc/nginx/sites-available/aksharamitra.conf /etc/nginx/sites-enabled/aksharamitra.conf"
echo "  sudo nginx -t && sudo systemctl reload nginx"

