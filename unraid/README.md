# Unraid Installation Guide

Indygestion is a multi-container application (8 services). There are two ways to install it on Unraid.

---

## Option A: Docker Compose Manager (Recommended)

This gives you the cleanest experience — one stack, one management point.

### 1. Install Docker Compose Manager plugin

1. Go to **Apps** tab in Unraid
2. Search for **"Docker Compose Manager"** (by dcflacern)
3. Click **Install**

### 2. Add the Indygestion stack

1. Go to **Docker** tab → **Compose** sub-tab (added by the plugin)
2. Click **Add New Stack**
3. Set:
   - **Name:** `indygestion`
   - **Source:** Git Repository
   - **Repository URL:** `https://github.com/SloPOS/indygestion.git`
   - **Branch:** `main`
4. Click **Save**

### 3. Configure

1. Click the stack name to edit
2. Click **Edit .env** and set at minimum:
   - `APP_PORT=4708`
   - `MEDIA_ROOT_HOST=/mnt/user/indygestion`
   - `POSTGRES_PASSWORD=` (set a strong password)
   - `TUSD_WEBHOOK_SECRET=` (set any random string)
3. Save

### 4. Start

1. Click **Compose Up** on the stack
2. Wait for all 8 containers to start (first build takes a few minutes)
3. Open `http://your-unraid-ip:4708`

### Managing

- **Start/Stop/Restart:** Use the Compose Manager UI
- **Update:** Pull latest from git, then Compose Up with rebuild
- **Logs:** Click individual containers or use `docker compose logs` via SSH

---

## Option B: SSH Bootstrap Script

If you prefer command-line or don't want to install the Compose Manager plugin.

### 1. SSH into your Unraid server

```bash
ssh root@your-unraid-ip
```

### 2. Run the bootstrap script

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SloPOS/indygestion/main/scripts/bootstrap-unraid.sh)
```

### 3. Customize (optional)

```bash
INSTALL_DIR=/mnt/user/appdata/indygestion \
MEDIA_ROOT_HOST=/mnt/user/indygestion \
bash <(curl -fsSL https://raw.githubusercontent.com/SloPOS/indygestion/main/scripts/bootstrap-unraid.sh)
```

### 4. Access

Open `http://your-unraid-ip:4708`

---

## Prepare media storage

Whichever method you use, create your media share first:

1. Go to **Shares** in Unraid
2. Click **Add Share**
3. Name: `indygestion`
4. Set cache/mover preferences as desired (cache=prefer is good for active projects)

The app expects this structure (created automatically):
```
/mnt/user/indygestion/
├── projects/     ← active project files
├── staging/      ← upload landing zone
├── archive/      ← compressed finished projects
└── _review/      ← clips awaiting assignment
```

---

## Intel QSV (Hardware Transcoding)

If your Unraid server has an Intel CPU with integrated graphics (like the i7-8700K):

1. Verify iGPU is available: `ls -la /dev/dri/`
2. The docker-compose.yml already mounts `/dev/dri` for QSV-enabled containers
3. No additional configuration needed

---

## Ports

| Port | Purpose |
|------|---------|
| 4708 (default) | Web UI, API, and uploads — all via nginx |

All other services (database, redis, whisper, worker) are internal only.
