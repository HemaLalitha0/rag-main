# AksharaMitra (అక్షరమిత్ర) – Hostinger VPS Production Deployment Guide

**Parent Company:** SHR Trinity  
**Product:** AksharaMitra (అక్షరమిత్ర) – AI-Powered Bilingual Reading Intelligence & Personalized Learning Platform  
**Target Live URL:** `https://aksharamitra.shrtrinity.com`  
**Reference Production Site (Untouched):** `https://finpilot.shrtrinity.com`  
**Isolated Server Directory:** `/opt/shrtrinity/aksharamitra`  
**Container Port Mapping:** `127.0.0.1:8510` (VPS Host) → `8501` (Streamlit Container)

---

## 1. Hostinger Hosting Compatibility (VPS vs. Shared Hosting)

- **Hostinger Shared / Web Hosting:** **Not supported.** Shared hosting only serves static HTML/PHP websites and does not permit persistent Python 3.11 processes, WebSockets (`/_stcore/stream`), Docker containers, or custom Nginx reverse-proxy configurations.
- **Hostinger KVM VPS (Recommended: KVM 2 or higher, Ubuntu 24.04 LTS):** **Fully supported.** Provides root SSH access, Docker & Docker Compose, Nginx, Certbot SSL, and persistent execution.
- **Sharing the Existing FinPilot Ubuntu VPS (`189.72.150.225`):** Because `finpilot.shrtrinity.com` already runs on Ubuntu with `nginx/1.24.0`, AksharaMitra can run safely alongside FinPilot in its own isolated directory (`/opt/shrtrinity/aksharamitra`), Docker container (`shr_aksharamitra_app`), port (`127.0.0.1:8510`), and Nginx virtual host (`aksharamitra.conf`) **without modifying or restarting FinPilot**.

---

## 2. Step-by-Step DNS Configuration (Hostinger hPanel)

> **Safety Rule:** Do **not** edit or delete the existing `finpilot` DNS record.

1. Log in to **Hostinger hPanel** → **Domains** → **`shrtrinity.com`** → **DNS / Nameservers**.
2. Add a **new `A` record**:
   - **Type:** `A`
   - **Name (Host):** `aksharamitra`
   - **Points to (IPv4):** `189.72.150.225` *(or your new Hostinger VPS IPv4 address)*
   - **TTL:** `3600` (or default)
3. Verify DNS propagation from any terminal:
   ```bash
   nslookup aksharamitra.shrtrinity.com
   ```

---

## 3. Hostinger VPS Prerequisite Setup (Ubuntu 24.04)

Connect to your Hostinger VPS via SSH (`ssh <user>@<VPS_IP>`), then inspect available server resources first:

```bash
# 1. Inspect available RAM, disk space, and running services
free -h
df -h /
sudo ss -tuln | grep -E ':80|:443|:8510'
```

If Docker, Docker Compose, Nginx, or Certbot are not yet installed on the VPS:

```bash
# 2. Update packages and install Docker, Nginx, and Certbot
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git nginx certbot python3-certbot-nginx

# Install Docker Engine & Docker Compose plugin (if not already installed)
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# Verify installations
docker --version
docker compose version
nginx -v
```

---

## 4. Exact Deployment Commands (In Execution Order)

### Step 1: Create Isolated Directory & Clone Repository
```bash
sudo mkdir -p /opt/shrtrinity/aksharamitra
sudo chown -R "$USER":"$USER" /opt/shrtrinity/aksharamitra

git clone https://github.com/HemaLalitha0/rag-main.git /opt/shrtrinity/aksharamitra
cd /opt/shrtrinity/aksharamitra
```

### Step 2: Configure Host-Only Secrets (Outside Docker Image & Git)
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
nano .streamlit/secrets.toml
# Fill in your API keys if needed, save (Ctrl+O, Enter), and exit (Ctrl+X)
chmod 600 .streamlit/secrets.toml
```

### Step 3: Build and Start AksharaMitra Container (Port `127.0.0.1:8510`)
```bash
chmod +x deploy/deploy_aksharamitra.sh
./deploy/deploy_aksharamitra.sh
```

*(This script checks RAM/disk/port `8510`, initializes persistent volumes for `users.db`, `data/`, `kb_cache/`, and `pdfs/`, builds the Docker image, starts `shr_aksharamitra_app` with `restart: unless-stopped`, and validates `http://127.0.0.1:8510/_stcore/health`.)*

---

## 5. Nginx Reverse Proxy & HTTPS SSL Setup

> **Safety Rule:** This creates a separate Nginx config file (`aksharamitra.conf`) and never touches FinPilot's Nginx config.

### Step 1: Install Temporary HTTP Reverse Proxy for Certbot Verification
```bash
sudo tee /etc/nginx/sites-available/aksharamitra.conf > /dev/null <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name aksharamitra.shrtrinity.com;

    location / {
        proxy_pass http://127.0.0.1:8510;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/aksharamitra.conf /etc/nginx/sites-enabled/aksharamitra.conf
sudo nginx -t
sudo systemctl reload nginx
```

### Step 2: Provision Free Let's Encrypt HTTPS Certificate via Certbot
```bash
sudo certbot --nginx -d aksharamitra.shrtrinity.com --redirect
```

### Step 3: Verify Auto-Renewal
```bash
sudo certbot renew --dry-run
```

---

## 6. Post-Deployment Live Verification Steps

Run these checks after deployment:

```bash
# 1. Verify AksharaMitra container is healthy
docker ps --filter "name=shr_aksharamitra_app"
curl -fsS http://127.0.0.1:8510/_stcore/health

# 2. Verify AksharaMitra HTTPS endpoint
curl -I https://aksharamitra.shrtrinity.com

# 3. Verify FinPilot AI is completely unaffected
curl -I https://finpilot.shrtrinity.com
```

In a web browser, open **`https://aksharamitra.shrtrinity.com`** and confirm:
1. HTTPS padlock is valid and browser tab shows **AksharaMitra | అక్షరమిత్ర – SHR Trinity**.
2. Top header displays the **SHR Trinity** logo and **AksharaMitra (అక్షరమిత్ర)** branding.
3. All 5 screens work cleanly (*Student Dashboard*, *Reading Assessment*, *AI Reading Analysis*, *Assessment Results*, *Teacher Dashboard*).
4. WebSocket interactions (switching grade/language/student profile) respond immediately without disconnect errors.
5. `https://finpilot.shrtrinity.com` still loads FinPilot AI normally.

---

## 7. Rollback Instructions (If Deployment Fails)

To cleanly stop and remove AksharaMitra without affecting FinPilot AI or any other SHR Trinity service:

```bash
# 1. Stop and remove the AksharaMitra Docker container (preserves your data volumes)
cd /opt/shrtrinity/aksharamitra
docker compose down

# 2. Disable the AksharaMitra Nginx virtual host
sudo rm -f /etc/nginx/sites-enabled/aksharamitra.conf
sudo nginx -t
sudo systemctl reload nginx

# 3. Confirm FinPilot AI is still running normally
curl -I https://finpilot.shrtrinity.com
```

*(Note: Your persistent data in `/opt/shrtrinity/aksharamitra/users.db`, `data/`, `kb_cache/`, and `pdfs/` remains safely preserved on disk for troubleshooting or redeployment.)*

