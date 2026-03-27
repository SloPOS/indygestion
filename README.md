# Indygestion

Self-hosted video ingest stack (React + FastAPI + Celery + Whisper + tusd) for large footage workflows.

## Features

- Resumable large-file uploads via **tusd** (network drop recovery)
- FastAPI backend with PostgreSQL + pgvector metadata storage
- Celery worker pipelines for ingest orchestration
- Whisper transcription service + transcript-driven similarity grouping hooks
- Proxy generation + archive workflow foundations (FFmpeg/QSV-enabled)
- USB/SD device watcher service for direct media ingest
- Unraid-friendly Docker Compose deployment model

## Quickstart (works now)

### Option A) One-shot bootstrap (download + configure + run)

If the repo is public:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SloPOS/indygestion/main/scripts/bootstrap-unraid.sh)
```

Optional overrides:

```bash
INSTALL_DIR=/mnt/user/appdata/indygestion \
MEDIA_ROOT_HOST=/mnt/user/indygestion \
REPO_BRANCH=main \
bash <(curl -fsSL https://raw.githubusercontent.com/SloPOS/indygestion/main/scripts/bootstrap-unraid.sh)
```

### Option B) Pull + run install script (repo already downloaded)

```bash
chmod +x scripts/install-unraid.sh
./scripts/install-unraid.sh
```

If the repo is private, clone first:

```bash
git clone https://github.com/SloPOS/indygestion.git
cd indygestion
chmod +x scripts/install-unraid.sh
./scripts/install-unraid.sh
```

### Option B) Manual install

### 1) Prepare media directory

Create your host media root (default in this repo: `/media/indygestion`):

```bash
sudo mkdir -p /media/indygestion/{projects,staging,archive,_review}
```

> On Unraid, set `MEDIA_ROOT_HOST` to your share path (for example `/mnt/user/indygestion`).

### 2) Configure env

```bash
cp .env.example .env
```

Minimum values to review:
- `POSTGRES_PASSWORD`
- `TUSD_WEBHOOK_SECRET`
- `MEDIA_ROOT_HOST`
- `MACVLAN_PARENT`, `MACVLAN_SUBNET`, `MACVLAN_GATEWAY`
- `APP_IP` (dedicated nginx LAN IP on macvlan)

### 3) Validate compose

```bash
docker compose config
```

### 4) Build + run

```bash
docker compose up -d --build
```

### 5) Smoke checks

```bash
docker compose ps
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:9000/health
```

## Service map

Everything routes through a single nginx reverse proxy on port **80**.

On Unraid, nginx can be attached directly to `br0` with its own dedicated LAN IP via Docker macvlan (default `192.168.86.85`).

| Path | Service | Description |
|------|---------|-------------|
| `/` | Frontend | Web UI |
| `/api/` | Backend | FastAPI REST API |
| `/files/` | tusd | Resumable upload endpoint |

All internal services (postgres, redis, whisper, worker, device-watcher) are **not** exposed to the host — only nginx is reachable on its dedicated macvlan IP.

To change where nginx is reachable on your LAN, set `APP_IP` in `.env` (and adjust `MACVLAN_*` values if your Unraid network differs).

## Notes

- Single-port architecture: browser talks to nginx only; nginx proxies to internal services.
- tusd completion webhook fires internally to backend (container-to-container).
- Worker and backend task names are aligned (`tasks.*`) so queued jobs are consumable by the worker.
- `worker` and `backend` mount `/dev/dri` for Intel QSV.
- `device-watcher` is privileged by design for USB/SD detection.
- On Unraid, all containers share a `indygestion-` prefix for easy identification.
